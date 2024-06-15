import flask
import numpy as np
import datetime

app = flask.Flask(__name__)

# Set up a separate radar state daemon that keeps track of whether radar is running, feedback / messages from radar,
# data from GNSS etc. This daemon is accessed to update the webpage


@app.route("/")
def home():
    return flask.render_template("index.html")


@app.route("/_get_gnss")
def get_gnss():
    dt = str(datetime.datetime.now())
    date = dt.split(" ")[0]
    time = dt.split(" ")[1].split(".")[0]
    llh = np.random.rand(3) * 90
    return flask.jsonify(
        fix="3D-GNSS",
        date=date,
        time=time,
        lon="%.3f" % llh[0],
        lat="%.3f" % llh[1],
        hgt="%.3f" % llh[2],
    )


@app.route("/_get_radar")
def get_radar():
    return flask.jsonify(ntrc="69", nbuf="420", prf="2000", adc="25e6")


if __name__ == "__main__":
    app.run(debug=True)
