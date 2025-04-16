import os
from queue import Queue
import requests

IP = "http://127.0.0.1"
PORT = ":1337"

PROMPT_1 = "Think of different Aspects (or better: sub-concepts) of the Concept '"
PROMPT_2 = "'. Before you output a COMMA-SEPERATED LIST, you MUST output 'START_OF_LIST'. Limit yourself to a maximum of 5. Only name the most important. Make sure that you cover a variety of aspects. Make sure to exclude duplicates."

concept_queue = Queue()
graph_nodes = {};

class GraphNode:
    def __init__(self, val="Empty"):
        self.value = val
        self.ingoing = []
        self.outgoing = []

    def connect_to(self, other_id:str):
        other = graph_nodes.get(other_id);
        if other == None:
            print("Node", other_id, "not found!")
            return
        else:
            self.outgoing.append(other)
            other.ingoing.append(self)

def new_node(name:str = "Empty"):
    if graph_nodes.get(name) != None:
        # print("Node", name, "already exists!")
        return None
    else:
        graph_nodes[name] = GraphNode(name)
        return graph_nodes[name]
    
def connect_nodes(a:str, b:str):
    if graph_nodes.get(a) != None:
        graph_nodes[a].connect_to(b)


class TreeNode:
    def __init__(self, value, is_dup = False):
        self.value = value
        self.children = []
        self.is_dup = is_dup

    def add_child(self, child):
        self.children.append(child)


GRAPH_ROOT = GraphNode()
TREE_ROOT = TreeNode("Empty")
QUEUE_MARKER = TreeNode("__end")

def get_models():
    req = requests.get(IP+PORT+"/v1/models")
    json = req.json()
    result = []
    for key in json["data"]:
        if key.get("status") != None and key["status"] == "downloaded":
            result.append(key["id"])
    return result

class color:
   PURPLE = '\033[95m'
   CYAN = '\033[96m'
   DARKCYAN = '\033[36m'
   BLUE = '\033[94m'
   GREEN = '\033[92m'
   YELLOW = '\033[93m'
   RED = '\033[91m'
   BOLD = '\033[1m'
   UNDERLINE = '\033[4m'
   END = '\033[0m'

def print_tree_rec(node:TreeNode, cur_depth=0, cur_node=None):
    print("    "*cur_depth, end="")

    if node == cur_node:
        print(color.BOLD, node.value+':', color.END)
    else:
        print(node.value + ':')
    
    for c in node.children:
        print_tree_rec(c, cur_depth+1, cur_node)

def print_tree(node:TreeNode, cur_node=None):
    os.system('cls' if os.name == 'nt' else 'clear')
    print_tree_rec(node, 0, cur_node)

def main_loop(model, depth):
    while depth >= 0:
        while not concept_queue.empty():
            tn = concept_queue.get()
            if tn == QUEUE_MARKER:
                depth -= 1
                break

            print_tree(TREE_ROOT, tn)

            resp = requests.post(IP+PORT+"/v1/chat/completions", json= {
                "messages": [{
                    "role": "user",
                    "content": PROMPT_1 + tn.value + PROMPT_2
                }],
                "model": model
            })

            # TODO: filter out reasoning tokens
            answer = resp.json()["choices"][0]["message"]["content"]
            arr = answer.split("START_OF_LIST")
            if len(arr) == 1:
                continue
            list = arr[1]
            new_words = list.split(",")
            print(tn.value + ": ", end="")
            print(new_words)
            for nw in new_words:
                nw = nw.strip()
                nn = new_node(nw)
                if nn == None: # if node already exists
                    new_tn = TreeNode(nw, True)
                else:
                    new_tn = TreeNode(nw, False)
                tn.add_child(new_tn)

                connect_nodes(tn.value, nw)
                concept_queue.put(new_tn)
                print_tree(TREE_ROOT, tn)

            concept_queue.put(QUEUE_MARKER)


def main():
    models = get_models()
    # print out models to choose
    print("Choose an available model:")
    for i, m in enumerate(models):
        print(str(i) + ":", m)
    num = -1
    while num < 0 or num > len(models)-1:
        num = int(input("(0-"+ str(len(models)-1) +") > "))

    id = models[num]
    for m in models:
        if m != id:
            resp = requests.post(IP+PORT+"/v1/models/stop", json={"model": m})
            # print(str(resp.status_code) + ": " + resp.text)
    print("Starting Model..")

    resp = requests.post(IP+PORT+"/v1/models/start", json={"model": id})
    if resp.status_code == 200:
        print("Model started successfully");
    else:
        print("Error while starting model: ");
        print(str(resp.status_code) + ': ' + resp.text);
    
    concept = input("Please enter the concept you wish to explore: ");
    GRAPH_ROOT = new_node(concept)
    TREE_ROOT.value = concept

    concept_queue.put(TREE_ROOT)
    concept_queue.put(QUEUE_MARKER)

    depth = input("Depth (default is 3): ")
    try: 
        depth = int(depth)
    except:
        depth = 3

    if depth < 1:
        depth = 1
    
    main_loop(id, depth)

if __name__ == "__main__":
    main()
