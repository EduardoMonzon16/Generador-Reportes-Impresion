"""
Aplicación Flask para procesamiento de reportes de impresión.

Este módulo contiene una aplicación web que permite a los usuarios
autenticarse y procesar archivos CSV de reportes de impresión,
generando archivos Excel con tablas dinámicas y filtros aplicados.
"""
import os
import io
import sys
import tempfile
from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash
import mysql.connector
import pandas as pd
import chardet
import xlwings as xw
from dotenv import load_dotenv
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.styles import Font

# =============================================================================
# CONFIGURACIÓN DE LA APLICACIÓN
# =============================================================================

app = Flask(__name__)

# Cargar variables de entorno desde archivo .env
load_dotenv()

# Configurar secret_key desde variables de entorno
app.secret_key = os.getenv('SECRET_KEY', 'clave_secreta_para_sesiones')

# Configuración de base de datos - CORREGIDA
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME'),
    'port': int(os.getenv('DB_PORT') or '3306'),
    'charset': 'utf8mb4',
    'autocommit': True,
    'connection_timeout': 10,
    'auth_plugin': 'mysql_native_password'
}

# Verificar que las variables de entorno estén configuradas
required_env_vars = ['DB_HOST', 'DB_USER', 'DB_PASSWORD', 'DB_NAME']
missing_vars = [var for var in required_env_vars if not os.getenv(var)]

if missing_vars:
    print(f"ERROR: Las siguientes variables de entorno no están "
          f"configuradas: {', '.join(missing_vars)}")
    print("Por favor, configura tu archivo .env")
    sys.exit(1)

# Configuración de filtros para reportes
FILTROS_CONFIG = {
    'SURCO - HP': {
        'impresora': 'HP LJ300-400 color M351-M451 PCL 6',
        'solo_impresora': True
    },
    'SURCO - XEROX': {
        'impresora': 'Xerox WorkCentre 3225',
        'solo_impresora': True
    },
    'SAN ISIDRO - EPSON': {
        'impresora': 'L4260 Series(Network)',
        'solo_impresora': True
    }
}

# Encabezados requeridos para el CSV
ENCABEZADOS_REQUERIDOS = [
    'Hora', 'Usuario', 'Páginas', 'Copias', 'Impresora',
    'Nombre Documento', 'Cliente', 'Formato Papel', 'Idioma',
    'Altura', 'Anchura', 'Frente/reverso', 'Escala de grises', 'Formato'
]

# =============================================================================
# FUNCIONES DE BASE DE DATOS - MEJORADAS
# =============================================================================

def conectar_db():
    """Establece conexión con la base de datos MySQL."""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            return connection
        return None
    except mysql.connector.Error as error:
        print(f"Error al conectar a la base de datos: {error}")
        return None


def validar_credenciales(usuario, password):
    """Valida las credenciales del usuario contra la base de datos."""
    conexion = None
    cursor = None

    try:
        conexion = conectar_db()
        if not conexion:
            flash('Error de conexión con la base de datos.', 'danger')
            return False

        cursor = conexion.cursor(buffered=True)
        sql = "SELECT Contraseña FROM usuarios WHERE Nombre = %s"
        cursor.execute(sql, (usuario,))
        resultado = cursor.fetchone()

        if resultado:
            contraseña_en_bd = resultado[0]
            return contraseña_en_bd == password
        return False

    except mysql.connector.InterfaceError as e:
        print(f"Error de interfaz de base de datos: {e}")
        flash('Error inesperado. Por favor, contacta al administrador.', 'danger')
        return False
    except mysql.connector.Error as e:
        print(f"Error en la conexión a la base de datos: {e}")
        flash('Error de conexión con la base de datos. Intenta más tarde.', 'danger')
        return False
    except (ValueError, TypeError) as e:
        print(f"Error de validación de datos: {e}")
        flash('Error inesperado. Por favor, contacta al administrador.', 'danger')
        return False
    finally:
        # Cerrar cursor y conexión para evitar memory leaks
        if cursor:
            cursor.close()
        if conexion and conexion.is_connected():
            conexion.close()

# =============================================================================
# FUNCIONES DE PROCESAMIENTO DE DATOS
# =============================================================================


def normalizar_encabezado(header):
    """Normaliza encabezados eliminando espacios y convirtiendo a minúsculas."""
    return str(header).strip().lower()


def validar_encabezados_csv(df):
    """Valida que el DataFrame contenga todos los encabezados requeridos."""
    encabezados_encontrados = [
        normalizar_encabezado(col)
        for col in df.columns.tolist()
    ]
    encabezados_requeridos_norm = [
        normalizar_encabezado(header)
        for header in ENCABEZADOS_REQUERIDOS
    ]

    encabezados_faltantes = [
        ENCABEZADOS_REQUERIDOS[i]
        for i, header_norm in enumerate(
            encabezados_requeridos_norm
        )
        if header_norm not in encabezados_encontrados
    ]

    return encabezados_faltantes


def procesar_dataframe(df):
    """Procesa el DataFrame agregando la columna de impresiones, 
    columna de fecha formateada y eliminando columnas innecesarias."""
    
    # Agregar la columna "Impresiones" en la posición F (índice 5, después de la nueva columna Mes Año)
    if len(df.columns) >= 5:  # Ahora necesitamos al menos 5 columnas (A, B, C, D, E)
        # Convertir las columnas C y D a numéricas (ahora índices 2 y 3)
        columna_c = pd.to_numeric(df.iloc[:, 2], errors='coerce').fillna(0)
        columna_d = pd.to_numeric(df.iloc[:, 3], errors='coerce').fillna(0)
        
        # Calcular las impresiones (C * D)
        impresiones = columna_c * columna_d
        
        # Insertar la columna "Impresiones" en la posición F (índice 5)
        df.insert(5, 'Impresiones', impresiones)
    
    # Agregar columna de fecha formateada basada en la columna A
    if len(df.columns) >= 1:
        # Convertir la columna A a datetime
        fechas = pd.to_datetime(df.iloc[:, 0], errors='coerce')
        
        # Diccionario para traducir meses al español
        meses_es = {
            1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
            5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
            9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
        }
        
        # Formatear las fechas como "Marzo 2025"
        fechas_formateadas = fechas.apply(lambda x: f"{meses_es[x.month]} - {x.year}" if pd.notna(x) else "")
        
        # Insertar la columna "Mes Año" en la posición B (índice 1)
        df.insert(1, 'Mes - Año', fechas_formateadas)
    
    # Eliminar las columnas I, J, K, L (ahora serían índices 10, 11, 12, 13 debido a las nuevas columnas)
    columnas_a_eliminar = [i for i in [10, 11, 12, 13] if i < len(df.columns)]
    
    # Eliminar las columnas de forma descendente
    for indice in reversed(columnas_a_eliminar):
        df = df.drop(df.columns[indice], axis=1)
    
    return df

def filtrar_dataframe(df, config):
    """Filtra el DataFrame según la configuración proporcionada."""
    if config.get('solo_impresora', True):
        return df[df['Impresora'] == config['impresora']]
    return df[
        (df['Impresora'].str.contains(config['impresora'],
                                      case=False, na=False)) &
        (df['Cliente'].str.contains(config['cliente'],
                                    case=False, na=False))
    ]

# =============================================================================
# FUNCIONES DE EXCEL
# =============================================================================


def ajustar_ancho_columnas(sheet):
    """Ajusta automáticamente el ancho de las columnas en una hoja de Excel."""
    for column in sheet.columns:
        max_length = 0
        column_letter = column[0].column_letter

        for cell in column:
            try:
                if cell.value:
                    length = len(str(cell.value))
                    max_length = max(max_length, length)
            except (TypeError, AttributeError):
                pass

        adjusted_width = max_length + 2
        sheet.column_dimensions[column_letter].width = adjusted_width


def convertir_a_tabla(sheet, dataframe, nombre_tabla):
    """Convierte un rango de datos en una tabla de Excel con formato."""
    if dataframe.shape[0] == 0:
        return None

    max_row = dataframe.shape[0] + 1
    max_col = dataframe.shape[1]

    # Calcular la letra de la columna final
    if max_col <= 26:
        end_col = chr(64 + max_col)
    else:
        end_col = (chr(64 + (max_col - 1) // 26) +
                   chr(65 + (max_col - 1) % 26))

    rango_tabla = f"A1:{end_col}{max_row}"

    # Crear tabla con estilo
    tabla = Table(displayName=nombre_tabla, ref=rango_tabla)
    style = TableStyleInfo(
        name="TableStyleLight11",
        showFirstColumn=False,
        showLastColumn=False,
        showRowStripes=True,
        showColumnStripes=False
    )
    tabla.tableStyleInfo = style
    sheet.add_table(tabla)

    # Aplicar fuente Calibri 14
    for row in range(1, max_row + 1):
        for col in range(1, max_col + 1):
            cell = sheet.cell(row=row, column=col)
            cell.font = Font(name="Calibri", size=14)

    # Autoajustar columnas
    ajustar_ancho_columnas(sheet)

    # Autoajustar altura de filas
    for row in sheet.iter_rows():
        sheet.row_dimensions[row[0].row].height = None

    return True


def crear_tabla_dinamica(wb, sheet_datos):
    """Crea una tabla dinámica en el libro de Excel."""
    try:
        # Crear nueva hoja para tabla dinámica
        sheet_pivot = wb.sheets.add('TABLA DINAMICA')

        # Obtener el rango de datos
        data_range = sheet_datos.range('A1').expand()
        sheet_name = sheet_datos.name
        source_data = f"'{sheet_name}'!{data_range.address}"

        # Crear PivotCache y PivotTable
        pivot_cache = wb.api.PivotCaches().Create(
            SourceType=1,  # xlDatabase
            SourceData=source_data
        )

        pivot_table = pivot_cache.CreatePivotTable(
            TableDestination=sheet_pivot.range('C3').api,
            TableName='TablaDinamica1'
        )

        # Aplicar formato
        pivot_range = pivot_table.TableRange2
        pivot_range.Font.Name = "Calibri"
        pivot_range.Font.Size = 14
        pivot_table.TableStyle2 = "PivotStyleLight11"

        # Autoajustar columnas y filas
        pivot_range.Columns.AutoFit()
        pivot_range.Rows.AutoFit()

        # Configurar campos de la tabla dinámica
        pivot_table.PivotFields('Impresora').Orientation = 1  # xlRowField
        pivot_table.PivotFields('Impresora').Position = 1

        pivot_table.PivotFields('Usuario').Orientation = 1  # xlRowField
        pivot_table.PivotFields('Usuario').Position = 2

        # Agregar campo de valor
        data_field = pivot_table.AddDataField(
            pivot_table.PivotFields('Impresiones'),
            'Suma de Impresiones',
            -4157  # xlSum
        )
        data_field.NumberFormat = "#,##0"

        # Expandir campos
        pivot_table.PivotFields('Impresora').ShowDetail = True

        return True
    except (AttributeError, KeyError, ValueError) as e:
        print(f"Error al crear tabla dinámica: {e}")
        return False


def generar_excel(df):
    """Genera el archivo Excel completo con todas las hojas y formatos."""
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as temp_file:
        temp_path = temp_file.name

    # Crear archivo Excel básico con pandas
    with pd.ExcelWriter(temp_path, engine='openpyxl') as writer:
        # Hoja general
        df.to_excel(writer, index=False, sheet_name='GENERAL')

        # Hojas filtradas
        dataframes_filtrados = {}
        for nombre_hoja, config in FILTROS_CONFIG.items():
            df_filtrado = filtrar_dataframe(df, config)
            df_filtrado.to_excel(writer, index=False, sheet_name=nombre_hoja)
            dataframes_filtrados[nombre_hoja] = df_filtrado

        # Aplicar formato a todas las hojas
        workbook = writer.book

        # Formatear hoja general
        convertir_a_tabla(workbook['GENERAL'], df, "TablaGeneral")

        # Formatear hojas filtradas
        for nombre_hoja, df_filtrado in dataframes_filtrados.items():
            nombre_tabla = nombre_hoja.replace(' ', '_').replace('-', '_')
            convertir_a_tabla(workbook[nombre_hoja], df_filtrado,
                               f"Tabla{nombre_tabla}")

    # Crear tabla dinámica con xlwings
    try:
        app_xw = xw.App(visible=False)
        wb = app_xw.books.open(temp_path)

        try:
            sheet_datos = wb.sheets['GENERAL']
            crear_tabla_dinamica(wb, sheet_datos)
            wb.save()
        except (AttributeError, KeyError) as e:
            print(f"Error al crear tabla dinámica: {e}")
        finally:
            wb.close()
            app_xw.quit()

    except (ImportError, OSError) as e:
        print(f"Error con xlwings: {e}")

    return temp_path

# =============================================================================
# DECORADORES
# =============================================================================


def login_required(f):
    """Decorador para rutas que requieren autenticación."""
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# =============================================================================
# RUTAS DE LA APLICACIÓN
# =============================================================================


@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Ruta de inicio de sesión."""
    if request.method == 'POST':
        usuario = request.form['usuario']
        password = request.form['password']

        # Validaciones básicas
        if not usuario or not password:
            return render_template('login.html')

        if validar_credenciales(usuario, password):
            session['usuario'] = usuario
            return redirect(url_for('reportes'))
        flash('Usuario o contraseña incorrectos. Por favor, intenta nuevamente.',
              'danger')
        return render_template('login.html')

    return render_template('login.html')


@app.route('/logout')
def logout():
    """Ruta para cerrar sesión."""
    session.pop('usuario', None)
    return redirect(url_for('login'))


@app.route('/reportes')
@login_required
def reportes():
    """Ruta principal de reportes."""
    return render_template('reportes.html')


@app.route('/subir_csv', methods=['GET', 'POST'])
@login_required
def subir_csv():
    """Ruta para subir y procesar archivos CSV."""
    if request.method == 'GET':
        return render_template('reportes.html')

    # POST method handling
    archivo = request.files.get('archivo')

    # Validaciones básicas
    if not archivo or not archivo.filename:
        return render_template('reportes.html')

    if not archivo.filename.lower().endswith('.csv'):
        return render_template('reportes.html')

    try:
        # Detectar encoding del archivo
        data = archivo.read()
        result = chardet.detect(data)
        encoding = result['encoding']
        archivo.seek(0)

        # Leer CSV
        df = pd.read_csv(
            archivo,
            encoding=encoding or 'latin1',
            sep=',',
            skiprows=1,
            on_bad_lines='skip',
            index_col=False
        )

        # Validar encabezados
        encabezados_faltantes = validar_encabezados_csv(df)
        if encabezados_faltantes:
            return render_template('reportes.html')

        # Procesar DataFrame
        df = procesar_dataframe(df)

        # Generar archivo Excel
        temp_path = generar_excel(df)

        # Leer y devolver archivo
        with open(temp_path, 'rb') as f:
            output_data = f.read()

        output = io.BytesIO(output_data)
        output.seek(0)

        # Limpiar archivo temporal
        os.unlink(temp_path)

        return send_file(
            output,
            download_name="Reporte de Impresiones.xlsx",
            as_attachment=True,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except (pd.errors.EmptyDataError, pd.errors.ParserError,
            UnicodeDecodeError) as e:
        print(f"Error al procesar archivo: {e}")
        return render_template('reportes.html')

# =============================================================================
# PUNTO DE ENTRADA
# =============================================================================

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
