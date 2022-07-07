kubeadm init --pod-network-cidr=10.244.0.0/16 #--kubernetes-version 1.18.8

cp /etc/kubernetes/admin.conf $HOME/.kube/config
chown $(id -u):$(id -g) $HOME/.kube/config

CONTEXT=greenbrier
CONTEXT=home-gpu
MASTER=dudley-dowrong

CONTEXT=dahlia
MASTER=wftech-control-dahlia

kubectl --context $CONTEXT apply -f kube-flannel.yml


kubectl --context $CONTEXT taint nodes $MASTER node-role.kubernetes.io/master:NoSchedule-

kubectl --context $CONTEXT describe node $(kubectl --context $CONTEXT get nodes | grep master | awk '{print $1}')


kubectl --context $CONTEXT apply -f https://raw.githubusercontent.com/kubernetes/dashboard/v2.6.0/aio/deploy/recommended.yaml
kubectl --context $CONTEXT -n kubernetes-dashboard apply -f dash-user.yml
kubectl --context $CONTEXT -n kubernetes-dashboard describe secret $(kubectl --context $CONTEXT -n kubernetes-dashboard get secret | grep admin-user | awk '{print $1}')
kubectl --context $CONTEXT get nodes
kubectl --context $CONTEXT get pods --all-namespaces
kubectl --context $CONTEXT proxy



http://localhost:8001/api/v1/namespaces/kubernetes-dashboard/services/https:kubernetes-dashboard:/proxy/#/




kubectl --context $CONTEXT apply -f classroom-ns.yaml
kubectl --context $CONTEXT  apply -f minio.yaml
kubectl --context $CONTEXT  apply -f camera.yaml


kubectl --context $CONTEXT -n classroom port-forward service/minio 9000:9000


## Notes

Make sure iptables are cleared
Make sure ip link is clear of rubbish like a lingering flannel link
Restart docker after making those changes

apt install jq
sudo snap install yq


kubectl --context $CONTEXT -n classroom port-forward streamer-nppd5 8000:8000



curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
sudo python get-pip.py
sudo python -m pip install picamera



sudo apt-get update
sudo apt-get upgrade -y
sudo apt-get install -y libraspberrypi-dev python3-picamera/testing


animalflowerpot16candles


curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh


from time import sleep
from picamera import PiCamera

camera = PiCamera()
camera.resolution = (1024, 768)
camera.start_preview()
# Camera warm-up time
sleep(2)
camera.capture('/data/foo.jpg')



raspistill -o /data/image.jpg




kubectl --context $CONTEXT -n inference port-forward service/nsqadmin 4171:4171






kubectl --context home-gpu -n inference  get rabbitmqcluster rabbitmqcluster
