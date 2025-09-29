from database import conectar_base_datos

def mostrar_rutas():
    conn = conectar_base_datos()
    cur = conn.cursor(dictionary=True)

    print("\n=== TABLA configuracion_app ===")
    cur.execute("SELECT logo_app_ruta_relativa, hero_imagen_ruta_relativa, icono_hamburguesa_ruta_relativa, icono_cerrar_ruta_relativa FROM configuracion_app;")
    for row in cur.fetchall():
        print(row)

    print("\n=== TABLA secciones ===")
    cur.execute("SELECT id_seccion, nombre_seccion, icono_seccion FROM secciones;")
    for row in cur.fetchall():
        print(row)

    print("\n=== TABLA sub_secciones ===")
    cur.execute("SELECT id_sub_seccion, nombre_sub_seccion, imagen_ruta_relativa, icono_ruta_relativa, foto1_ruta_relativa, foto2_ruta_relativa, foto3_ruta_relativa, foto4_ruta_relativa FROM sub_secciones;")
    for row in cur.fetchall():
        print(row)

    cur.close()
    conn.close()

if __name__ == "__main__":
    mostrar_rutas()
