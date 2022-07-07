from fabric import Connection


PASSWORD = "animalflowerpot16candles"

hosts = [
    # "192.168.1.81",
    # "192.168.1.84",
    "192.168.1.85",
    # "192.168.1.80",
    # "192.168.1.45",
    # "192.168.1.78",
    # "192.168.1.10",
    # "192.168.1.17",
    # "192.168.1.47",
    # "192.168.1.46",
    # "192.168.1.18",
    # "192.168.1.12",
    # "192.168.1.13",
    # "192.168.1.8",
    # "192.168.1.9",
]

for host in hosts:
    c = Connection(host, user="wildflowertech", connect_kwargs={
        "password": PASSWORD,
    })
    print("starting %s" % host)
    print(c.run("date").stdout)
    try:
        c.sudo('k3s --version', password=PASSWORD, warn=True)
        c.sudo('systemctl status k3s-agent.service', password=PASSWORD, warn=True)
        try:
            print("stopping k3s if running")
            c.sudo('systemctl stop k3s-agent', password=PASSWORD, warn=True)
            print("            [OK]")
        except:
            print("            [FAILED]")
        try:
            print("uninstall k3s if installed")
            c.sudo('/usr/local/bin/k3s-uninstall.sh', password=PASSWORD, warn=True)
            print("            [OK]")
        except:
            print("            [FAILED]")
        try:
            print("install latest k3s")
            c.sudo('curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION=v1.16.7+k3s1 INSTALL_K3S_TYPE=exec K3S_URL=https://192.168.1.40:6443 K3S_TOKEN=K104d4f2e42b7fa33de18c5bdd1c528f8d5514f96fb7619316ed73499a58febac6b::server:359281a42639802c2ff24f66a4fef8e8 sh -', password=PASSWORD, warn=True, pty=True)
            print("            [OK]")
        except:
            print("            [FAILED]")
        c.sudo('systemctl stop k3s-agent.service', password=PASSWORD, warn=True, hide='both')
        try:
            c.sudo('rm /etc/systemd/system/k3s.service', password=PASSWORD, warn=True)
        except:
            pass
        c.sudo('systemctl daemon-reload', password=PASSWORD, warn=True)
        c.sudo('systemctl restart k3s-agent.service', password=PASSWORD, warn=True)
    except Exception as err:
      print("failed for node")
      print(err)

