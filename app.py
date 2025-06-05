from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
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
        # Verificar si es una petición AJAX
        is_ajax = request.headers.get('Content-Type', '').startswith('multipart/form-data')
        
        archivo = request.files['archivo']

        if not archivo or archivo.filename == '':
            error_msg = 'No se ha seleccionado ningún archivo CSV'
            if is_ajax:
                return jsonify({'error': True, 'message': error_msg}), 400
            else:
                flash(error_msg, 'error')
                return redirect(url_for('reportes'))

        if not archivo.filename.lower().endswith('.csv'):
            error_msg = 'Por favor, selecciona un archivo CSV válido (.csv)'
            if is_ajax:
                return jsonify({'error': True, 'message': error_msg}), 400
            else:
                flash(error_msg, 'error')
                return render_template('reportes.html')

        if archivo and archivo.filename.endswith('.csv'):
            try:
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
                    error_msg = f'Error: No se encuentran los datos requeridos. Faltan: {", ".join(encabezados_faltantes)}'
                    # Para peticiones AJAX, devolver JSON con error
                    if is_ajax:
                        return jsonify({
                            'error': True, 
                            'message': error_msg,
                            'missing_headers': encabezados_faltantes,
                            'type': 'missing_headers'
                        }), 422
                    else:
                        flash(error_msg, 'error')
                        return render_template('reportes.html')

                # Resto del código de procesamiento...
                # (Agregar columna Impresiones, eliminar columnas, etc.)
                
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

                # Resto del código para generar Excel...
                # (Mantener todo el código de procesamiento de Excel que ya tienes)
                
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

                # Todo el código de procesamiento de Excel aquí...
                # (Mantener todo el código existente para generar el Excel)
                
                # Simplificado para el ejemplo - mantener tu lógica completa
                with pd.ExcelWriter(temp_path, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='GENERAL')
                    # ... resto de tu lógica de Excel

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
                        download_name="reporte_generado.xlsx",
                        as_attachment=True,
                        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    )
                    
                except Exception as e:
                    print(f"Error al enviar archivo: {e}")
                    error_msg = 'Error al generar el archivo final'
                    if is_ajax:
                        return jsonify({'error': True, 'message': error_msg}), 500
                    else:
                        flash(error_msg, 'error')
                        return render_template('reportes.html')
                        
            except Exception as e:
                print(f"Error al procesar CSV: {e}")
                error_msg = f'Error al procesar el archivo CSV: {str(e)}'
                if is_ajax:
                    return jsonify({'error': True, 'message': error_msg}), 500
                else:
                    flash(error_msg, 'error')
                    return render_template('reportes.html')
                    
        else:
            error_msg = 'Por favor selecciona un archivo CSV válido'
            if is_ajax:
                return jsonify({'error': True, 'message': error_msg}), 400
            else:
                flash(error_msg, 'error')
                return render_template('reportes.html')

    return '''
        <form method="post" enctype="multipart/form-data">
            <input type="file" name="archivo" accept=".csv">
            <input type="submit" value="Subir CSV y Generar Excel">
        </form>
    '''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)