#!/bin/bash

sudo systemctl enable --now systemd-resolved.service

sudo curl -fsSLo /usr/share/keyrings/kubernetes-archive-keyring.gpg https://dl.k8s.io/apt/doc/apt-key.gpg
echo "deb [signed-by=/usr/share/keyrings/kubernetes-archive-keyring.gpg] https://apt.kubernetes.io/ kubernetes-xenial main" | sudo tee /etc/apt/sources.list.d/kubernetes.list

sudo curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update -y
sudo apt upgrade -y

echo "Install pip"
sudo apt install pip -y

echo "Install yq"

sudo wget -qO /usr/local/bin/yq https://github.com/mikefarah/yq/releases/latest/download/yq_linux_arm
sudo chmod a+x /usr/local/bin/yq

echo "Install Docker"

curl -sSL https://get.docker.com/ | sudo sh

echo "Install Containerd"

sudo rm /etc/containerd/config.toml
sudo sh -c 'cat << EOF > /etc/containerd/config.toml
disabled_plugins = []
imports = []
oom_score = 0
plugin_dir = ""
required_plugins = []
root = "/var/lib/containerd"
state = "/run/containerd"
temp = ""
version = 2

[cgroup]
path = ""

[debug]
address = ""
format = ""
gid = 0
level = ""
uid = 0

[grpc]
address = "/run/containerd/containerd.sock"
gid = 0
max_recv_message_size = 16777216
max_send_message_size = 16777216
tcp_address = ""
tcp_tls_ca = ""
tcp_tls_cert = ""
tcp_tls_key = ""
uid = 0

[metrics]
address = ""
grpc_histogram = false

[plugins]

[plugins."io.containerd.gc.v1.scheduler"]
deletion_threshold = 0
mutation_threshold = 100
pause_threshold = 0.02
schedule_delay = "0s"
startup_delay = "100ms"

[plugins."io.containerd.grpc.v1.cri"]
device_ownership_from_security_context = false
disable_apparmor = false
disable_cgroup = false
disable_hugetlb_controller = true
disable_proc_mount = false
disable_tcp_service = true
enable_selinux = false
enable_tls_streaming = false
enable_unprivileged_icmp = false
enable_unprivileged_ports = false
ignore_image_defined_volumes = false
max_concurrent_downloads = 3
max_container_log_line_size = 16384
netns_mounts_under_state_dir = false
restrict_oom_score_adj = false
sandbox_image = "registry.k8s.io/pause:3.6"
selinux_category_range = 1024
stats_collect_period = 10
stream_idle_timeout = "4h0m0s"
stream_server_address = "127.0.0.1"
stream_server_port = "0"
systemd_cgroup = false
tolerate_missing_hugetlb_controller = true
unset_seccomp_profile = ""

[plugins."io.containerd.grpc.v1.cri".cni]
bin_dir = "/opt/cni/bin"
conf_dir = "/etc/cni/net.d"
conf_template = ""
ip_pref = ""
max_conf_num = 1

[plugins."io.containerd.grpc.v1.cri".containerd]
default_runtime_name = "runc"
disable_snapshot_annotations = true
discard_unpacked_layers = false
ignore_rdt_not_enabled_errors = false
no_pivot = false
snapshotter = "overlayfs"

[plugins."io.containerd.grpc.v1.cri".containerd.default_runtime]
base_runtime_spec = ""
cni_conf_dir = ""
cni_max_conf_num = 0
container_annotations = []
pod_annotations = []
privileged_without_host_devices = false
runtime_engine = ""
runtime_path = ""
runtime_root = ""
runtime_type = ""

[plugins."io.containerd.grpc.v1.cri".containerd.default_runtime.options]

[plugins."io.containerd.grpc.v1.cri".containerd.runtimes]

[plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc]
base_runtime_spec = ""
cni_conf_dir = ""
cni_max_conf_num = 0
container_annotations = []
pod_annotations = []
privileged_without_host_devices = false
runtime_engine = ""
runtime_path = ""
runtime_root = ""
runtime_type = "io.containerd.runc.v2"

[plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc.options]
BinaryName = ""
CriuImagePath = ""
CriuPath = ""
CriuWorkPath = ""
IoGid = 0
IoUid = 0
NoNewKeyring = false
NoPivotRoot = false
Root = ""
ShimCgroup = ""
SystemdCgroup = true

[plugins."io.containerd.grpc.v1.cri".containerd.untrusted_workload_runtime]
base_runtime_spec = ""
cni_conf_dir = ""
cni_max_conf_num = 0
container_annotations = []
pod_annotations = []
privileged_without_host_devices = false
runtime_engine = ""
runtime_path = ""
runtime_root = ""
runtime_type = ""

[plugins."io.containerd.grpc.v1.cri".containerd.untrusted_workload_runtime.options]

[plugins."io.containerd.grpc.v1.cri".image_decryption]
key_model = "node"

[plugins."io.containerd.grpc.v1.cri".registry]
config_path = ""

[plugins."io.containerd.grpc.v1.cri".registry.auths]

[plugins."io.containerd.grpc.v1.cri".registry.configs]

[plugins."io.containerd.grpc.v1.cri".registry.headers]

[plugins."io.containerd.grpc.v1.cri".registry.mirrors]

[plugins."io.containerd.grpc.v1.cri".x509_key_pair_streaming]
tls_cert_file = ""
tls_key_file = ""

[plugins."io.containerd.internal.v1.opt"]
path = "/opt/containerd"

[plugins."io.containerd.internal.v1.restart"]
interval = "10s"

[plugins."io.containerd.internal.v1.tracing"]
sampling_ratio = 1.0
service_name = "containerd"

[plugins."io.containerd.metadata.v1.bolt"]
content_sharing_policy = "shared"

[plugins."io.containerd.monitor.v1.cgroups"]
no_prometheus = false

[plugins."io.containerd.runtime.v1.linux"]
no_shim = false
runtime = "runc"
runtime_root = ""
shim = "containerd-shim"
shim_debug = false

[plugins."io.containerd.runtime.v2.task"]
platforms = ["linux/amd64"]
sched_core = false

[plugins."io.containerd.service.v1.diff-service"]
default = ["walking"]

[plugins."io.containerd.service.v1.tasks-service"]
rdt_config_file = ""

[plugins."io.containerd.snapshotter.v1.aufs"]
root_path = ""

[plugins."io.containerd.snapshotter.v1.btrfs"]
root_path = ""

[plugins."io.containerd.snapshotter.v1.devmapper"]
async_remove = false
base_image_size = ""
discard_blocks = false
fs_options = ""
fs_type = ""
pool_name = ""
root_path = ""

[plugins."io.containerd.snapshotter.v1.native"]
root_path = ""

[plugins."io.containerd.snapshotter.v1.overlayfs"]
root_path = ""
upperdir_label = false

[plugins."io.containerd.snapshotter.v1.zfs"]
root_path = ""

[plugins."io.containerd.tracing.processor.v1.otlp"]
endpoint = ""
insecure = false
protocol = ""

[proxy_plugins]

[stream_processors]

[stream_processors."io.containerd.ocicrypt.decoder.v1.tar"]
accepts = ["application/vnd.oci.image.layer.v1.tar+encrypted"]
args = ["--decryption-keys-path", "/etc/containerd/ocicrypt/keys"]
env = ["OCICRYPT_KEYPROVIDER_CONFIG=/etc/containerd/ocicrypt/ocicrypt_keyprovider.conf"]
path = "ctd-decoder"
returns = "application/vnd.oci.image.layer.v1.tar"

[stream_processors."io.containerd.ocicrypt.decoder.v1.tar.gzip"]
accepts = ["application/vnd.oci.image.layer.v1.tar+gzip+encrypted"]
args = ["--decryption-keys-path", "/etc/containerd/ocicrypt/keys"]
env = ["OCICRYPT_KEYPROVIDER_CONFIG=/etc/containerd/ocicrypt/ocicrypt_keyprovider.conf"]
path = "ctd-decoder"
returns = "application/vnd.oci.image.layer.v1.tar+gzip"

[timeouts]
"io.containerd.timeout.bolt.open" = "0s"
"io.containerd.timeout.shim.cleanup" = "5s"
"io.containerd.timeout.shim.load" = "5s"
"io.containerd.timeout.shim.shutdown" = "3s"
"io.containerd.timeout.task.state" = "2s"

[ttrpc]
address = ""
gid = 0
uid = 0
EOF'

sudo mkdir -p /data/capture_output
sudo chmod 0755 /data/capture_output
sudo chown $USER:$USER /data/capture_output

sudo mkdir -p /data/scripts
sudo chown $USER:$USER /data/scripts

pip install --upgrade v4l2-python3

sudo sh -c 'apt-mark unhold kubeadm && \
apt-get update && apt-get install -y kubeadm=1.27.1-00 && \
apt-mark hold kubeadm'

sudo sh -c 'apt-mark unhold kubelet kubectl && \
apt-get update && apt-get --allow-downgrades install -y kubelet=1.27.1-00 kubectl=1.27.1-00 && \
apt-mark hold kubelet kubectl'

sudo systemctl restart kubelet
sudo systemctl restart containerd
sudo systemctl daemon-reload
