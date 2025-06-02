from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask import send_file
import pandas as pd
import io
import chardet

app = Flask(__name__)
app.secret_key = 'clave_secreta_para_sesiones'

# Ruta principal: muestra el formulario de login
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        password = request.form['password']

        # Validación básica (sustituye por lógica real)
        if usuario == 'admin' and password == '1234':
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

    if request.method == 'POST':
        archivo = request.files['archivo']

        if archivo and archivo.filename.endswith('.csv'):
            data = archivo.read()
            result = chardet.detect(data)
            encoding = result['encoding']
            archivo.seek(0)  # vuelve al inicio del archivo

            df = pd.read_csv(archivo, encoding=encoding or 'latin1', sep=',', skiprows=1, on_bad_lines='skip', index_col=False)

            # Filtra según la columna "Impresora" (ajusta el nombre de columna si es otro)
            df_surco_hp = df[(df['Impresora'] == 'HP LJ300-400 color M351-M451 PCL 6') & (df['Cliente'].str.contains('SURCO', case=False, na=False))]
            df_surco_xerox = df[df['Impresora'].str.contains('Xerox WorkCentre 3225', case=False, na=False) & df['Cliente'].str.contains('SURCO', case=False, na=False)]
            df_san_isidro_epson = df[df['Impresora'].str.contains('L4260 Series(Network)', case=False, na=False) & df['Cliente'].str.contains('SAN ISIDRO', case=False, na=False)]

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='GENERAL')
                df_surco_hp.to_excel(writer, index=False, sheet_name='SURCO - HP')
                df_surco_xerox.to_excel(writer, index=False, sheet_name='SURCO - XEROX')
                df_san_isidro_epson.to_excel(writer, index=False, sheet_name='SAN ISIDRO - EPSON')

                # Aquí obtenemos el workbook y agregamos autofiltro a cada hoja
                workbook = writer.book

                # Función para agregar autofiltro a una hoja
                def agregar_autofiltro(hoja, df):
                    # La primera fila es la de encabezados
                    max_row = df.shape[0] + 1  # +1 por encabezado
                    max_col = df.shape[1]
                    # Rango de autofiltro (Ejemplo: A1 hasta la última columna y fila con datos)
                    hoja.auto_filter.ref = f"A1:{chr(64 + max_col)}{max_row}"

                # Agregamos autofiltro a cada hoja creada
                agregar_autofiltro(workbook['GENERAL'], df)
                agregar_autofiltro(workbook['SURCO - HP'], df_surco_hp)
                agregar_autofiltro(workbook['SURCO - XEROX'], df_surco_xerox)
                agregar_autofiltro(workbook['SAN ISIDRO - EPSON'], df_san_isidro_epson)

                # Filtra y guarda para SURCO - HP
                filtro_hp = df[df['Impresora'] == 'HP LJ300-400 color M351-M451 PCL 6']
                filtro_hp.to_excel(writer, index=False, sheet_name='SURCO - HP')

                # Filtra y guarda para SURCO - XEROX
                filtro_hp = df[df['Impresora'] == 'Xerox WorkCentre 3225']
                filtro_hp.to_excel(writer, index=False, sheet_name='SURCO - XEROX')

                # Filtra y guarda para SAN ISIDRO - EPSON
                filtro_hp = df[df['Impresora'] == 'L4260 Series(Network)']
                filtro_hp.to_excel(writer, index=False, sheet_name='SAN ISIDRO - EPSON')

            output.seek(0)  # Reinicia el puntero del archivo

            # Devuelve el archivo para descarga
            return send_file(output,
                             download_name="reporte_generado.xlsx",
                             as_attachment=True,
                             mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

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