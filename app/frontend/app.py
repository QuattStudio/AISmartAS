from flask import Flask, render_template
import os
import signal

app = Flask(__name__)


@app.route("/")
def home():
  return render_template("index.html", username="Kartik")

@app.route("/shutdown")
def shutdown():
    os.kill(os.getpid(), signal.SIGINT)
    return "Server shutting down..."


# if __name__ == "__main__":
#   app.run(debug=True)

