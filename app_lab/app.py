import logging
import os
import sqlite3
from flask import Flask, g, redirect, render_template, request, session, url_for

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "huellavet.db")
LOG_PATH = os.path.join(BASE_DIR, "huellavet.log")

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-lab-only")

# Configuración de logging hacia app_lab/huellavet.log
logger = logging.getLogger("huellavet")
logger.setLevel(logging.INFO)
if not logger.handlers:
    file_handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
    formatter = logging.Formatter(
        "%(asctime)s | IP=%(ip)s | USUARIO=%(usuario)s | RUTA=%(ruta)s | EVENTO=%(evento)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


def get_db():
    """Obtiene una conexión SQLite por petición."""
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Inicializa la base de datos SQLite local con datos 100% ficticios."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS expedientes (
            id INTEGER PRIMARY KEY,
            mascota TEXT NOT NULL,
            dueno_id INTEGER NOT NULL,
            diagnostico TEXT NOT NULL,
            notas TEXT NOT NULL,
            FOREIGN KEY (dueno_id) REFERENCES usuarios (id)
        )
        """
    )

    cursor.executemany(
        "INSERT OR IGNORE INTO usuarios (id, username, password) VALUES (?, ?, ?)",
        [
            (1, "ana", "1234"),
            (2, "roberto", "5678"),
        ],
    )

    cursor.executemany(
        "INSERT OR IGNORE INTO expedientes (id, mascota, dueno_id, diagnostico, notas) VALUES (?, ?, ?, ?, ?)",
        [
            (1, "Firulais", 1, "Vacuna antirrábica", "Cliente al corriente"),
            (2, "Michi", 2, "Cirugía menor", "Pago pendiente $1,500 - Tel: 8110002222"),
        ],
    )

    conn.commit()
    conn.close()


@app.after_request
def log_request(response):
    """Registra fecha/hora, IP, usuario actual, ruta visitada y resultado de login/acceso."""
    ip = request.remote_addr or "-"
    usuario = session.get("username", "anonimo")
    ruta = request.full_path.rstrip("?")
    evento = getattr(g, "evento_log", f"VISITA ({response.status_code})")

    logger.info(
        "",
        extra={
            "ip": ip,
            "usuario": usuario,
            "ruta": ruta,
            "evento": evento,
        },
    )
    return response


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        db = get_db()
        # Vulnerabilidad SQL Injection por concatenación directa
        query = (
            "SELECT id, username FROM usuarios "
            f"WHERE username = '{username}' AND password = '{password}'"
        )

        try:
            cursor = db.cursor()
            cursor.execute(query)
            user = cursor.fetchone()
        except sqlite3.Error as exc:
            g.evento_log = f"LOGIN_ERROR_SQL (intento={username})"
            error = f"Error en la consulta SQL: {exc}"
            return render_template("login.html", error=error), 400

        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            g.evento_log = "LOGIN_EXITOSO"
            return redirect(url_for("index"))

        g.evento_log = f"LOGIN_FALLIDO (intento={username})"
        error = "Usuario o contraseña incorrectos."

    return render_template("login.html", error=error)


@app.route("/buscar", methods=["GET"])
def buscar():
    q = request.args.get("q", "")
    resultados = []

    if q:
        db = get_db()
        resultados = db.execute(
            """
            SELECT e.id, e.mascota, e.diagnostico, u.username AS dueno
            FROM expedientes e
            JOIN usuarios u ON e.dueno_id = u.id
            WHERE e.mascota LIKE ? OR e.diagnostico LIKE ?
            """,
            (f"%{q}%", f"%{q}%"),
        ).fetchall()

    # Vulnnerabilidad XSS reflejado en buscar.html usando | safe
    return render_template("buscar.html", q=q, resultados=resultados)


@app.route("/expediente/<int:exp_id>", methods=["GET"])
def expediente(exp_id):
    if "user_id" not in session:
        g.evento_log = "ACCESO_DENEGADO_SIN_SESION"
        return redirect(url_for("login"))

    db = get_db()
    # Vulnerabilidad  IDOR/BOLA (no valida que dueno_id == session["user_id"])
    registro = db.execute(
        """
        SELECT e.id, e.mascota, e.dueno_id, e.diagnostico, e.notas, u.username AS dueno_nombre
        FROM expedientes e
        JOIN usuarios u ON e.dueno_id = u.id
        WHERE e.id = ?
        """,
        (exp_id,),
    ).fetchone()

    if registro is None:
        g.evento_log = f"EXPEDIENTE_NO_ENCONTRADO (id={exp_id})"
        return render_template("expediente.html", registro=None, exp_id=exp_id), 404

    g.evento_log = f"CONSULTA_EXPEDIENTE (id={exp_id})"
    return render_template("expediente.html", registro=registro, exp_id=exp_id)


init_db()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
