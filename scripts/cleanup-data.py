from fabric import Connection


PASSWORD = "animalflowerpot16candles"

hosts = [
    # "192.168.1.45",
    "192.168.1.10",
    "192.168.1.17",
    "192.168.1.47",
    "192.168.1.46",
    "192.168.1.18",
    "192.168.1.12",
    "192.168.1.13",
    "192.168.1.8",
    "192.168.1.9",
]

for host in hosts:
    c = Connection(host, user="wildflowertech", connect_kwargs={
        "password": PASSWORD,
    })
    print("starting %s" % host)
    print(c.run("date").stdout)
    try:
        print("create runnyeggs.sh")
        c.sudo("echo \"find /data -name 'video-*'| sudo xargs rm -f\" > runnyeggs.sh", password=PASSWORD, warn=True)
        print("removing things")
        c.sudo("sh runnyeggs.sh", password=PASSWORD, warn=True)
        print("remove runnyeggs.sh")
        c.sudo("rm runnyeggs.sh", password=PASSWORD, warn=True)
    except Exception as err:
      print("failed for node")
      print(err)
