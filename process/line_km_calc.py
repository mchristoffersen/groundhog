import sys
import pandas as pd
import numpy as np
import pyproj

cols = ["date", "time", "latitude", "longitude", "height", "Q", "ns", "sdn", "sde", "sdu", "sdne", "sdeu", "sdun", "age", "ratio"]
df = pd.read_csv(sys.argv[1], comment="%", names=cols, delim_whitespace=True)

geo = "+proj=longlat +datum=WGS84 +no_defs"
utm = "+proj=utm +zone=6 +datum=WGS84 +units=m +no_defs"

x, y, z = pyproj.transform(
        geo, utm, df["longitude"].to_numpy(), df["latitude"].to_numpy(), df["height"].to_numpy(),
)

dx = np.diff(x)
dy = np.diff(y)

dist = np.sum(np.sqrt(dx**2 + dy**2))

print(dist/1e3)
