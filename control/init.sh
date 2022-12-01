sudo sysctl -w net.core.wmem_max=24862979
sudo sysctl -w net.core.rmem_max=24862979

for ((i=0;i<$(nproc);i++)); do sudo cpufreq-set -c $i -r -g performance; done
