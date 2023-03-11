# CUWB Stream

Capture UWB UDP packets and decode them into meaningful messages.

## Test

```
cd cuwb_stream
pip install -r development.txt
REPO_NAME=<<CUSTOM PPA CIHOLAS CREATED FOR WILDFLOWER>> pytest ./tests 
```

## Production

This app is deployed in our classroom K8 environment. A K8 NodePort is created to 
redirect traffic from the node (i.e Control PC) into the Pod environment. The Logger
binds to the UDP port where data is being redirected.

### CDP Logger

If you need to capture the CDP data stream while running the Logger in the K8 cluster,
you will need to multicast the UDP traffic. Unfortunately, we can't bind the CDP Logger
to the UDP port AND create the NodePort. Only one connection can be active at once.
The following steps are how to install `samplicator` in order to duplicate the UDP data
and send it to multiple ports.

#### Samplicator

##### Install

1) `mkdir -p ~/Wildflower && cd ~/Wildflower`
2) `git checkout https://github.com/sleinen/samplicator`
3) `cd samplicator && sudo apt-get install autoconf automake -y`
4) `sudo sh -c './autogen.sh && ./configure && make && make install'`

#### Run

1) Stop the CUWB Manager
2) Update the Manager's Output Port to 7673
3) Start the Manager
4) Start samplicate: `samplicate -d 1 -p 7673 0.0.0.0/7675 0.0.0.0/32222 1> /dev/null &`
5) Start the cdp-logger:

    ```
   mkdir -p ~/Wildflower/cuwb-logs && mkdir -p ~/Wildflower/cuwb-logs/output && mkdir -p ~/Wildflower/cuwb-logs/input && cd ~/Wildflower/cuwb-logs
   # Start logger on output data stream
   cd ~/Wildflower/cuwb-logs/output && cdp-logger -u 0.0.0.0:7675 &
   # Start logger on input data stream
   cd ~/Wildflower/cuwb-logs/input && cdp-logger -u 0.0.0.0:7667 &
    ```
6) Stop the cdp-logger by bringing apps back in to foreground and ctrl+c'ing them or by finding and killing their PIDs
7) Stop the Manager, set the Output port back to 32222, and start the Manager
