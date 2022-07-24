from flask import Flask, render_template, request, send_file, redirect, jsonify, url_for, make_response
import json, sqlite3
import os.path


class Response:
    def __init__(self, id, card, type, verbatim, loc=None) -> None:
        self.id = id
        self.card = card
        self.type = type
        self.verbatim = verbatim
        self.loc = loc


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
user_db_path = os.path.join(BASE_DIR, "data/users.db")
fq_db_path = os.path.join(BASE_DIR, "data/FQ_tables.db")

app = Flask("RorschachInkblotTest")


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/test", methods=['GET', 'POST'])
def test():
    phase = request.args.get('phase', type=str)
    no = request.args.get('no', type=int)
    id = request.args.get('id', type=int)

    if phase == 'response':
        return render_template("response_phase.html", phase=phase, no=no, src=f'static/img/blot_{no}.jpg', id=id)

    elif phase == 'inquiry':
        return render_template("inquiry_phase.html", phase=phase, no=no, id=id)

    else:
        return render_template("home.html")


@app.route("/api/register/<id>", methods=['POST'])
def register(id):
    with sqlite3.connect(user_db_path) as con:
        cur = con.cursor()
        cur.execute("""INSERT INTO Users(UserID) VALUES(?)""", (int(id),))
        con.commit()
        return ('', 204)


@app.route("/api/response", methods=['POST'])
def response():
    res = request.json

    if res['phase'] == 'response':
        with sqlite3.connect(user_db_path) as con:
            cur = con.cursor()
            if len(cur.execute("""SELECT * FROM Users WHERE UserID=?""", (res['id'],)).fetchall()) == 1:
                for v in res['verbatim']:
                    cur.execute("""INSERT INTO Responses(UserID, Card, Response) VALUES(?,?,?)""",
                                (int(res['id']), int(res['no']), v))
                    con.commit()
            else:
                return redirect("/")

        if res['no'] == 10:
            return redirect(url_for("test", phase='inquiry', no=1, id=res['id']))
        else:
            return redirect(url_for("test", phase='response', no=res['no'] + 1, id=res['id']))

    elif res['phase'] == 'inquiry':
        if res['no'] == 10:
            return redirect(url_for("results"))
        else:
            return redirect(url_for("test", phase='inquiry', no=res['no'] + 1, id=res['id']))
    else:
        return "ERROR"


@app.route("/api/R/<id>", methods=['POST'])
def R(id):
    id = int(id)

    with sqlite3.connect(user_db_path) as con:
        cur = con.cursor()
        if len(cur.execute("""SELECT * FROM Users WHERE UserID=?""", (id,)).fetchall()) == 1:
            resp = make_response(
                jsonify(len(cur.execute("""SELECT * FROM Responses WHERE UserID=?""", (id,)).fetchall())))
            resp.headers['Content-type'] = 'application/json'
            return resp
        else:
            return None


if __name__ == "__main__":
    # app.run(host='0.0.0.0', port='8080', debug=True)
    pass