from flask import Flask, request
from flask_restful import Resource, Api
import docker
import json
import hashlib
import os

app = Flask(__name__)
api = Api(app)
client = docker.from_env()
node = client.images.pull("node:latest")

def copy_to(src, dst):
    name, dst = dst.split(':')
    container = client.containers.get(name)

    os.chdir(os.path.dirname(src))
    srcname = os.path.basename(src)
    tar = tarfile.open(src + '.tar', mode='w')
    try:
        tar.add(srcname)
    finally:
        tar.close()

    data = open(src + '.tar', 'rb').read()
    container.put_archive(os.path.dirname(dst), data)


@app.route('/')
def helloworld():
    return {'hello': 'world'}

@app.route('/run', methods=['POST'])
def run():
    req_data = request.get_json()
    container = client.containers.run(node, detach=True)
    h = hashlib.md5()
    # return req_data["language"]
    h.update(req_data["language"].encode('utf-8'))
    h.update("".join(req_data["code"]).encode('utf-8'))
    runningHash = h.hexdigest()


    filename = "/tmp/compiler/"+runningHash+"/javascript.js"
    dirname = os.path.dirname(filename)
    if not os.path.exists(dirname):
        os.makedirs(dirname, 755)
    with open(filename, "w+") as f:
        for item in req_data["code"]:
            f.write(item+" ")
        f.close() 

    resp = client.containers.run(
        image = node,
        command = ["node", "javascript.js"],
        volumes= {"/tmp/compiler/"+runningHash: {"bind": "/workspace", "mode": "rw"}},
        working_dir = "/workspace"
    )

   
    # copy_to('./app.py', container.name+':/app.js')
    # resp = container.exec_run(["node", "app.js"])
    # resp = client.containers.run(node detach=True)
    return resp
    return json.dumps({os.getcwd()+"/tmp/compiler/"+runningHash+"/" : {"bind": "/workspace", "mode": "rw"}})
        
@app.route('/version')
def version():
    v = client.version()
    return {'version': v}

@app.route('/docker/containers')
def containers():
    docker_containers = [container.id for container in client.containers.list()]
    return json.dumps(docker_containers)

@app.route('/docker/images')
def docker_images():
    docker_images = [image.tags for image in client.images.list()]
    return json.dumps(docker_images)

@app.route('/docker/images/prune')
def docker_images_prune():
    for container in client.containers.list():
        container.stop()
        
    client.images.prune(filters={'dangling': False})
    return 'true'

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')