from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask import send_file
from mysql.connector import Error
import mysql.connector
import pandas as pd
import io
import chardet
import tempfile
import xlwings as xw
import os

app = Flask(__name__)
app.secret_key = 'clave_secreta_para_sesiones'

def conectar():
    return mysql.connector.connect(
        host='localhost',          
        user='root',   
        password='Universitario12#',
        database='systembd',
        port=3307 
    )

# Función para validar credenciales
def validar_credenciales(usuario, password):
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        sql = "SELECT Contraseña FROM usuarios WHERE Nombre = %s"
        cursor.execute(sql, (usuario,))
        resultado = cursor.fetchone()
        cursor.close()
        conexion.close()

        if resultado:
            contraseña_en_bd = resultado[0]
            return contraseña_en_bd == password 
        else:
            return False
    except Error as e:
        print(f"Error en la conexión: {e}")
        return False

# Ruta principal: muestra el formulario de login
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        password = request.form['password']

        if validar_credenciales(usuario, password):
            session['usuario'] = usuario
            return redirect(url_for('reportes'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('login'))

@app.route('/reportes')
def reportes():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return render_template('reportes.html')



@app.route('/subir_csv', methods=['GET', 'POST'])
def subir_csv():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'GET':
        return render_template('reportes.html')

    if request.method == 'POST':
        archivo = request.files['archivo']

        if not archivo.filename.lower().endswith('.csv'):
            flash('Por favor, selecciona un archivo CSV válido (.csv)', 'error')
            return render_template('reportes.html')

        if archivo and archivo.filename.endswith('.csv'):
            data = archivo.read()
            result = chardet.detect(data)
            encoding = result['encoding']
            archivo.seek(0)  # vuelve al inicio del archivo

            df = pd.read_csv(archivo, encoding=encoding or 'latin1', sep=',', skiprows=1, on_bad_lines='skip', index_col=False)

            # Definir los encabezados requeridos
            encabezados_requeridos = [
                'Hora', 'Usuario', 'Páginas', 'Copias', 'Impresora', 
                'Nombre Documento', 'Cliente', 'Formato Papel', 'Idioma',
                'Altura', 'Anchura', 'Frente/reverso', 'Escala de grises', 'Formato'
            ]
            
            # Normalizar encabezados (quitar espacios y convertir a minúsculas para comparación)
            def normalizar_encabezado(header):
                return str(header).strip().lower()
            
            # Verificar si todos los encabezados requeridos están presentes
            encabezados_encontrados = [normalizar_encabezado(col) for col in df.columns.tolist()]
            encabezados_requeridos_norm = [normalizar_encabezado(header) for header in encabezados_requeridos]
            
            encabezados_faltantes = [
                encabezados_requeridos[i] for i, header_norm in enumerate(encabezados_requeridos_norm) 
                if header_norm not in encabezados_encontrados
            ]
            
            if encabezados_faltantes:
                flash(f'Error: No se encuentran los datos requeridos. Faltan: {", ".join(encabezados_faltantes)}', 'error')
                return render_template('reportes.html')

            # Agregar la columna "Impresiones" en la posición E (índice 4)
            if len(df.columns) >= 4:  # Verificar que tengamos al menos 4 columnas
                # Convertir las columnas C y D a numéricas, reemplazando valores no numéricos con 0
                columna_c = pd.to_numeric(df.iloc[:, 2], errors='coerce').fillna(0)
                columna_d = pd.to_numeric(df.iloc[:, 3], errors='coerce').fillna(0)
                
                # Calcular las impresiones (C * D)
                impresiones = columna_c * columna_d
                
                # Crear un nuevo DataFrame con la columna "Impresiones" insertada en la posición E
                df_nuevo = df.copy()
                df_nuevo.insert(4, 'Impresiones', impresiones)
                df = df_nuevo
            
            # Eliminar las columnas I, J, K, L (índices 8, 9, 10, 11) si existen
            columnas_a_eliminar = []
            if len(df.columns) > 8:  # Columna I
                columnas_a_eliminar.append(8)
            if len(df.columns) > 9:  # Columna J
                columnas_a_eliminar.append(9)
            if len(df.columns) > 10:  # Columna K
                columnas_a_eliminar.append(10)
            if len(df.columns) > 11:  # Columna L
                columnas_a_eliminar.append(11)
            
            # Eliminar las columnas de forma descendente para no afectar los índices
            for indice in reversed(columnas_a_eliminar):
                df = df.drop(df.columns[indice], axis=1)

            # Configuración de filtros
            filtros_config = {
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

            # Crear archivo temporal para xlwings
            temp_path = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False).name

            # Primero crear el archivo Excel básico con pandas
            with pd.ExcelWriter(temp_path, engine='openpyxl') as writer:
                # Hoja general
                df.to_excel(writer, index=False, sheet_name='GENERAL')
                
                # Diccionario para almacenar los DataFrames filtrados
                dataframes_filtrados = {}
                
                # Hojas filtradas
                for nombre_hoja, config in filtros_config.items():
                    if config.get('solo_impresora', True):
                        df_filtrado = df[df['Impresora'] == config['impresora']]
                    else:
                        df_filtrado = df[
                            (df['Impresora'].str.contains(config['impresora'], case=False, na=False)) & 
                            (df['Cliente'].str.contains(config['cliente'], case=False, na=False))
                        ]
                    
                    df_filtrado.to_excel(writer, index=False, sheet_name=nombre_hoja)
                    dataframes_filtrados[nombre_hoja] = df_filtrado
                
                # Aplicar formato y tablas
                workbook = writer.book
                
                def ajustar_ancho_columnas(sheet, dataframe):
                    for column in sheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        
                        for cell in column:
                            try:
                                if cell.value:
                                    length = len(str(cell.value))
                                    if length > max_length:
                                        max_length = length
                            except:
                                pass
                        
                        adjusted_width = max_length + 2
                        sheet.column_dimensions[column_letter].width = adjusted_width
                
                def convertir_a_tabla(sheet, dataframe, nombre_tabla):
                    from openpyxl.worksheet.table import Table, TableStyleInfo
                    from openpyxl.styles import PatternFill, Font
                    
                    if dataframe.shape[0] > 0:
                        max_row = dataframe.shape[0] + 1
                        max_col = dataframe.shape[1]
                        
                        if max_col <= 26:
                            end_col = chr(64 + max_col)
                        else:
                            end_col = chr(64 + (max_col - 1) // 26) + chr(65 + (max_col - 1) % 26)
                        
                        rango_tabla = f"A1:{end_col}{max_row}"
                        
                        tabla = Table(displayName=nombre_tabla, ref=rango_tabla)
                        
                        # Usar el mismo estilo que la tabla dinámica (TableStyleLight11)
                        style = TableStyleInfo(
                            name="TableStyleLight11",
                            showFirstColumn=False,
                            showLastColumn=False,
                            showRowStripes=True,
                            showColumnStripes=False
                        )
                        tabla.tableStyleInfo = style
                        
                        sheet.add_table(tabla)
                        
                        # Aplicar fuente Calibri 14 a toda la tabla (igual que la tabla dinámica)
                        for row in range(1, max_row + 1):
                            for col in range(1, max_col + 1):
                                cell = sheet.cell(row=row, column=col)
                                cell.font = Font(name="Calibri", size=14)
                        
                        # Autoajustar columnas y filas (igual que la tabla dinámica)
                        for column in sheet.columns:
                            max_length = 0
                            column_letter = column[0].column_letter
                            
                            for cell in column:
                                try:
                                    if cell.value:
                                        length = len(str(cell.value))
                                        if length > max_length:
                                            max_length = length
                                except:
                                    pass
                            
                            adjusted_width = max_length + 2
                            sheet.column_dimensions[column_letter].width = adjusted_width
                        
                        # Autoajustar altura de filas
                        for row in sheet.iter_rows():
                            sheet.row_dimensions[row[0].row].height = None  # Auto height
                
                # Aplicar formato a todas las hojas
                ajustar_ancho_columnas(workbook['GENERAL'], df)
                convertir_a_tabla(workbook['GENERAL'], df, "TablaGeneral")
                
                for nombre_hoja, df_filtrado in dataframes_filtrados.items():
                    ajustar_ancho_columnas(workbook[nombre_hoja], df_filtrado)
                    nombre_tabla = nombre_hoja.replace(' ', '_').replace('-', '_')
                    convertir_a_tabla(workbook[nombre_hoja], df_filtrado, f"Tabla{nombre_tabla}")

            # Ahora usar xlwings para crear la tabla dinámica
            try:
                app_xw = xw.App(visible=False)
                wb = app_xw.books.open(temp_path)
                
                try:
                    # Obtener la hoja GENERAL
                    sheet_datos = wb.sheets['GENERAL']
                    
                    # Crear nueva hoja para tabla dinámica
                    sheet_pivot = wb.sheets.add('TABLA DINAMICA')
                    
                    # Obtener el rango de datos
                    data_range = sheet_datos.range('A1').expand()
                    sheet_name = sheet_datos.name
                    
                    # Crear el rango completo para la tabla dinámica
                    source_data = f"'{sheet_name}'!{data_range.address}"
                    
                    # Crear PivotCache
                    pivot_cache = wb.api.PivotCaches().Create(
                        SourceType=1,  # xlDatabase
                        SourceData=source_data
                    )
                    
                    # Crear PivotTable
                    pivot_table = pivot_cache.CreatePivotTable(
                        TableDestination=sheet_pivot.range('C3').api,
                        TableName='TablaDinamica1'
                    )

                    # Obtener el rango de la tabla dinámica
                    pivot_range = pivot_table.TableRange2
                    
                    # Aplicar fuente Calibri 14 a toda la tabla dinámica
                    pivot_range.Font.Name = "Calibri"
                    pivot_range.Font.Size = 14

                    # Aplicar estilo de tabla dinámica predefinido "Verde claro, Estilo de tabla dinámica claro 11"
                    pivot_table.TableStyle2 = "PivotStyleLight11"
                    
                    # Autoajustar el ancho de las columnas de la tabla dinámica
                    pivot_range.Columns.AutoFit()
                    
                    # Autoajustar la altura de las filas de la tabla dinámica
                    pivot_range.Rows.AutoFit()
                    
                    # Configurar campos de la tabla dinámica
                    # Agregar 'Impresora' como campo de fila
                    pivot_table.PivotFields('Impresora').Orientation = 1  # xlRowField
                    pivot_table.PivotFields('Impresora').Position = 1
                    
                    # Agregar 'Usuario' como campo de fila
                    pivot_table.PivotFields('Usuario').Orientation = 1  # xlRowField
                    pivot_table.PivotFields('Usuario').Position = 2
                    
                    # Agregar 'Impresiones' como campo de valor
                    data_field = pivot_table.AddDataField(
                        pivot_table.PivotFields('Impresiones'),
                        'Suma de Impresiones',
                        -4157  # xlSum
                    )
                    
                    # Opcional: Configurar formato de números
                    data_field.NumberFormat = "#,##0"
                    
                    # Opcional: Expandir todos los campos
                    pivot_table.PivotFields('Impresora').ShowDetail = True
                    
                    # Guardar el archivo
                    wb.save()
                    
                except Exception as e:
                    print(f"Error al crear tabla dinámica: {e}")
                    # Si falla la tabla dinámica, al menos devolver el archivo básico
                    pass
                finally:
                    wb.close()
                    app_xw.quit()
                    
            except Exception as e:
                print(f"Error con xlwings: {e}")
                # Si xlwings falla completamente, continuar sin tabla dinámica
                pass

            # Leer el archivo final y devolverlo para descarga
            try:
                with open(temp_path, 'rb') as f:
                    output_data = f.read()
                
                # Crear BytesIO para enviar el archivo
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
                
            except Exception as e:
                print(f"Error al enviar archivo: {e}")
                flash('Error al generar el archivo final', 'error')
                
        else:
            flash('Por favor selecciona un archivo CSV válido', 'error')

    return '''
        <form method="post" enctype="multipart/form-data">
            <input type="file" name="archivo" accept=".csv">
            <input type="submit" value="Subir CSV y Generar Excel">
        </form>
    '''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)