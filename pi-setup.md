## Install

### Create image

> Use Raspberry Pi OS 64-bit Lite from 2023-05-03

### EDIT THE SD CARD BEFORE BOOTING PI

#### Edit /boot/cmdline.txt

> Prepend the cmdline.txt file with:
>
```
cgroup_enable=cpuset cgroup_memory=1 cgroup_enable=memory
```

#### Create Wildflower config metadata file

> Create /boot/wildflower-config.yml with:
```
hostname: <<CAMERA NAME>>
device_id: <<CAMERA DEVICE ID>>
environment-id: <<CLASSROOM ENVIRONMENT ID>>
assignment-id: <<CAMERA ASSIGNMENT ID>>
```

### RUN ON PI

> Change the hostname on /etc/hostname

```
sudo sh -c 'echo "<<CAMERA NAME>>" > /etc/hostname'
```

> Create and run the setup script (setup_pi_64.sh can be found in the repository):

`./setup_pi_64.sh`

> Join the classroom kube cluster:

```
sudo kubeadm join 192.168.128.38:6443 \
--discovery-token <<DISCOVERY TOKEN>> \
--discovery-token-ca-cert-hash <<DISCOVERY TOKEN HASH>>
```

### RUN ON CONTROL PC

> Add appropriate k8 labels to the new node
```
kubectl label node <<CAMERA NAME>> wf-type=camera
kubectl label node <<CAMERA NAME>> wildflower-type=camera
kubectl label node <<CAMERA NAME>> wf-camera-type=v2
```