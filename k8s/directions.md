Use the attached config for all the kubectl calls
=======================================================

If for some reason you need to Kube dashboard:
run this to get the token
```
kubectl --kubeconfig greenbrier.kube.config -n kubernetes-dashboard describe secret $(kubectl --kubeconfig greenbrier.kube.config -n kubernetes-dashboard get secret|grep admin|awk '{print $1}') | grep token | awk '{print $2}' | pbcopy
```

then run this to proxy the requests.

```
kubectl --kubeconfig greenbrier.kube.config proxy
```

Hit this url in your browser:
`http://localhost:8001/api/v1/namespaces/kubernetes-dashboard/services/https:kubernetes-dashboard:/proxy/#/`


=======================================================
Minio access:

Run this to proxy requests to minio:
```
kubectl --kubeconfig greenbrier.kube.config -n classroom port-forward service/minio 9000:9000
```

Then hit `http://localhost:9000/` to get the GUI.  Access is `wildflower-classroom/892347428463011457756120837563764010019`

find the videos bucket on the left nav.  In there are the folders for each camera using assignment ID. Browse to find the cam you are working with and find the latest time. videos are arranged by `ASSIGNMENT/YEAR/MM/DD/HH/MM-SS.mp4`

You may need to wait up to 20 seconds to get a video that reflects changes you have made.  Below is a list of camera names and assignment IDs.  The number in the name is the same as the number of the cable and switch port.

+------------------------+-----------------------------------------+
| name                   |   assignment-id                         |
+------------------------+-----------------------------------------+
| wildflower-tech-gb001  |   31b82f34-e2bd-448b-9920-778e47d59b43  |
| wildflower-tech-gb002  |   d52be5c6-a98e-4e98-a048-7f489d8f297c  |
| wildflower-tech-gb003  |   b36db10f-7e44-4dcb-b747-d96a4209fda1  |
| wildflower-tech-gb004  |   3c4bbe65-f18b-4e56-949f-6e0af9fbcad0  |
| wildflower-tech-gb005  |   731c4436-9a6a-4a49-92cd-92fc302c4290  |
| wildflower-tech-gb006  |   7ca1d766-e864-4b0f-b237-b0abd90af89e  |
| wildflower-tech-gb007  |   a6a66298-7829-4b89-b4ea-7373c7d29942  |
| wildflower-tech-gb008  |   32030b18-ab24-4863-8673-27a8bfdeb18d  |
| wildflower-tech-gb009  |   ef88e41a-f646-4304-a420-f37e4dda58a1  |
| wildflower-tech-gb010  |   f52770cd-9383-42fe-8e17-db8047034776  |
| wildflower-tech-gb011  |   1a3e9f9b-a2cd-4900-9f91-9257e8fc93dd  |
| wildflower-tech-gb012  |   9e8050fa-1ca5-4182-8b6d-6cca81b27404  |
| wildflower-tech-gb013  |   52a92a49-4a5a-44fc-a3fe-f59ac2f2319f  |
+------------------------+-----------------------------------------+

