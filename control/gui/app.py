import h5py
import numpy as np
import matplotlib.pyplot as plt
from dash import Dash, html, dcc, Input, Output, callback
import plotly.express as px
import scipy
import socket
import os
import ubx

# Load sample data
with h5py.File("./20240326T233154_groundhog0009.h5", mode="r") as fd:
    rx = fd["raw/rx0"][:]
    ppp = fd["drv/ppp0"][:]
    fs = fd["raw/rx0"].attrs["fs"]
    pre_trig = fd["raw/rx0"].attrs["pre_trig"]

# Filter data
sos = scipy.signal.butter(4, [1e6, 9e6], btype="band", output="sos", fs=fs)
rx = scipy.signal.sosfiltfilt(sos, rx, axis=0).astype(np.float32)

# Dash app
app = Dash(__name__)

# Initialize plots
zero_margin = {"l": 0, "r": 0, "b": 0, "t": 0}
pre1d = px.line(x=np.zeros(500), y=np.linspace(0, 10, 500), width=260, height=640)
pre1d.update_yaxes(range=[10, 0], autorange=False)
pre1d.update_traces(line_color="#000000", line_width=2)
pre1d.update_layout(margin=zero_margin, yaxis_title=None, xaxis_title=None)

pre2d = px.imshow(
    np.zeros((500, 500)),
    aspect="auto",
    color_continuous_scale="greys",
    zmin=0,
    zmax=1,
    x=np.arange(500),
    y=np.linspace(0, 10, 500),
    width=1100,
    height=640,
)
pre2d.update_yaxes(range=[10, 0], autorange=False)
pre2d.update_layout(
    coloraxis_showscale=False,
    margin=zero_margin,
    paper_bgcolor="white",
    plot_bgcolor="white",
)

app.layout = html.Div(
    [
        dcc.Interval(
            id="update-interval", interval=1 * 1000, n_intervals=0  # in milliseconds
        ),
        html.Div(
            [
                dcc.RangeSlider(
                    0,
                    20,
                    2,
                    value=[10, 20],
                    marks={i: str(20 - i) for i in range(0, 21, 2)},
                    vertical=True,
                    allowCross=False,
                    verticalHeight=600,
                    id="twtt-slider",
                )
            ],
            style={
                "width": "100px",
                "height": "640px",
                "left": "40px",
                "top": "40px",
                "position": "absolute",
                "display": "flex",
                "justify-content": "center",
            },
        ),
        html.Div(
            [
                dcc.Slider(
                    0,
                    4,
                    0.5,
                    value=2,
                    id="gain-slider",
                )
            ],
            style={
                "width": "400px",
                "height": "160px",
                "left": "1480px",
                "top": "40px",
                "position": "absolute",
            },
        ),
        html.Div(
            [dcc.Graph(id="preview2D", figure=pre2d, config={"staticPlot": True})],
            style={
                "width": "1000px",
                "height": "640px",
                "left": "140px",
                "top": "40px",
                "position": "absolute",
            },
        ),
        html.Div(
            [dcc.Graph(id="preview1D", figure=pre1d, config={"staticPlot": True})],
            style={
                "width": "260px",
                "height": "640px",
                "left": "1180px",
                "top": "40px",
                "position": "absolute",
            },
        ),
        html.Table(
            [
                html.Tr([html.Td("nTrc:"), html.Td()]),
                html.Tr([html.Td("nBuf:"), html.Td()]),
                html.Tr([html.Td("PRF:"), html.Td()]),
                html.Tr([html.Td("ADC:"), html.Td()]),
            ],
            id="Radar_status_table",
            style={
                "width": "400px",
                "height": "304px",
                "left": "1480px",
                "top": "120px",
                "position": "absolute",
            },
        ),
        html.Table(
            [
                html.Tr([html.Td("Fix:"), html.Td()]),
                html.Tr([html.Td("Date:"), html.Td()]),
                html.Tr([html.Td("Time:"), html.Td()]),
                html.Tr([html.Td("Lon:"), html.Td()]),
                html.Tr([html.Td("Lat:"), html.Td()]),
                html.Tr([html.Td("Hgt:"), html.Td()]),
            ],
            id="GNSS_status_table",
            style={
                "width": "400px",
                "height": "456px",
                "left": "1480px",
                "top": "464px",
                "position": "absolute",
            },
        ),
        html.Button(
            "Start",
            id="start",
            n_clicks=0,
            style={"left": "240px", "top": "910px", "position": "absolute"},
            className="start",
        ),
        html.Button(
            "Stop",
            id="stop",
            n_clicks=0,
            style={"left": "840px", "top": "910px", "position": "absolute"},
            className="stop",
        ),
        html.Div(
            [],
            id="radar_printout",
            style={
                "width": "1400px",
                "height": "180px",
                "left": "40px",
                "top": "700px",
                "position": "absolute",
                "background": "#FFFFFF",
                "border-radius": "10px",
                "border": "black 4px solid",
            },
        ),
    ]
)


@callback(
    [Output("GNSS_status_table", "children"), Output("GNSS_status_table", "style")],
    Input("update-interval", "n_intervals"),
)
def update_gnss(n):
    # Style for GNSS info box
    style = {
        "width": "400px",
        "height": "456px",
        "left": "1480px",
        "top": "464px",
        "position": "absolute",
        "background": "#00FF00",
    }

    # Initialize socket for GNSS
    socket_path = "/tmp/gps"
    # Create the Unix socket client
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    # Connect to the server
    try:
        client.connect(socket_path)
    except FileNotFoundError:
        return (
            [
                html.Tr([html.Td("Fix:"), html.Td("NO SOCK")]),
                html.Tr([html.Td("Date:"), html.Td()]),
                html.Tr([html.Td("Time:"), html.Td()]),
                html.Tr([html.Td("Lon:"), html.Td()]),
                html.Tr([html.Td("Lat:"), html.Td()]),
                html.Tr([html.Td("Hgt:"), html.Td()]),
            ],
            style,
        )

    msg = client.recv(1024)

    data = ubx.parse.nav.ubx_nav_pvt(b"\x00\x00" + msg)

    date = "%04d-%02d-%02d" % (data["year"], data["month"], data["day"])
    time = "%02d:%02d:%02d" % (data["hour"], data["min"], data["sec"])

    fixDict = {
        0: "No Fix",
        1: "DR",
        2: "2D-GNSS",
        3: "3D-GNSS",
        4: "GNSS + DR",
        5: "Time Only",
    }

    fix = fixDict[data["fixType"]]

    if data["fixType"] in [0, 5]:
        style["background"] = "#FF0000"
    elif data["fixType"] in [1, 2, 4]:
        style["background"] = "#FF6E00"

    return (
        [
            html.Tr([html.Td("Fix:"), html.Td(fix)]),
            html.Tr([html.Td("Date:"), html.Td(date)]),
            html.Tr([html.Td("Time:"), html.Td(time)]),
            html.Tr([html.Td("Lon:"), html.Td("%.5f" % (data["lon"] * 1e-7))]),
            html.Tr([html.Td("Lat:"), html.Td("%.5f" % (data["lat"] * 1e-7))]),
            html.Tr([html.Td("Hgt:"), html.Td("%.3f" % (data["height"] * 1e-3))]),
        ],
        style,
    )


cmt = """
@callback(
    [Output("GNSS_status_table", "children"), Output("GNSS_status_table", "style")],
    Input("update-interval", "n_intervals"),
)
def update_gnss_fake(n):
    datetime = ppp["utc"][n].decode()
    date, time = datetime.split("T")
    time = time.split(".")[0]

    fix = "3D-GNSS"
    style = {
        "width": "400px",
        "height": "456px",
        "left": "1480px",
        "top": "464px",
        "position": "absolute",
        "background": "#00FF00",
    }
    if n < 10:
        style["background"] = "#FF0000"
        fix = "None"

    return (
        [
            html.Tr([html.Td("Fix:"), html.Td(fix)]),
            html.Tr([html.Td("Date:"), html.Td(date)]),
            html.Tr([html.Td("Time:"), html.Td(time)]),
            html.Tr([html.Td("Lon:"), html.Td("%.5f" % ppp["lon"][n])]),
            html.Tr([html.Td("Lat:"), html.Td("%.5f" % ppp["lat"][n])]),
            html.Tr([html.Td("Hgt:"), html.Td("%.3f" % ppp["hgt"][n])]),
        ],
        style,
    )
"""


@callback(
    Output("Radar_status_table", "children"), Input("update-interval", "n_intervals")
)
def update_radar(n):
    datetime = ppp["utc"][n].decode()
    date, time = datetime.split("T")
    time = time.split(".")[0]

    return [
        html.Tr([html.Td("nTrc:"), html.Td(n)]),
        html.Tr([html.Td("nBuf:"), html.Td(2000)]),
        html.Tr([html.Td("PRF:"), html.Td(1000)]),
        html.Tr([html.Td("ADC:"), html.Td(25)]),
    ]


@callback(
    Output("preview1D", "figure"),
    [
        Input("update-interval", "n_intervals"),
        Input("twtt-slider", "value"),
        Input("gain-slider", "value"),
    ],
)
def update_1d(n, trange, gain):
    zero_margin = {"l": 0, "r": 0, "b": 0, "t": 0}
    t = 1e6 * (np.arange(rx.shape[0]) - pre_trig) / fs
    gain = np.arange(rx.shape[0]) ** gain
    pre1d = px.line(x=rx[:, n] * gain, y=t, width=260, height=640)
    pre1d.update_yaxes(range=[20 - trange[0], 20 - trange[1]], autorange=False)
    pre1d.update_traces(line_color="#000000", line_width=2)
    pre1d.update_layout(margin=zero_margin, yaxis_title=None, xaxis_title=None)
    return pre1d


@callback(
    Output("preview2D", "figure"),
    [
        Input("update-interval", "n_intervals"),
        Input("twtt-slider", "value"),
        Input("gain-slider", "value"),
    ],
)
def update_2d(n, trange, gain):
    n += 1
    zero_margin = {"l": 0, "r": 0, "b": 0, "t": 0}
    t = 1e6 * (np.arange(rx.shape[0]) - pre_trig) / fs

    # Form image
    gain = np.arange(rx.shape[0]) ** gain
    img = np.zeros((rx.shape[0], 500), dtype=np.float32) + np.nan
    img[:, 0 : min(n, 500)] = rx[:, max(0, n - 500) : n] * gain[:, np.newaxis]

    # Fix axpect raito of image
    width = 1100
    height = 640

    pre2d = px.imshow(
        img,
        aspect="auto",
        color_continuous_scale="greys",
        zmin=np.percentile(img, 1),
        zmax=np.percentile(img, 99),
        x=np.arange(img.shape[1]),
        y=t,
        width=width,
        height=height,
    )
    pre2d.update_yaxes(range=[20 - trange[0], 20 - trange[1]], autorange=False)
    pre2d.update_layout(
        coloraxis_showscale=False,
        margin=zero_margin,
        paper_bgcolor="white",
        plot_bgcolor="white",
    )
    return pre2d


if __name__ == "__main__":
    app.run(debug=True)
