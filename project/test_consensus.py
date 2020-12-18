import argparse
import math
import pickle
import numpy as np
import time

from Raft.Abstraction.send import send_post
import threading

# Load the pickle files
actions = pickle.load(open("data/actions.pickle", "rb"))
states = pickle.load(open("data/states.pickle", "rb"))
timestep = 0

def readout_state():
    return states[timestep]

def execute_action(action):
    #print(action)
    #print(actions[timestep])
    for k in action.keys():
        assert(action[k] == actions[timestep][k])

def get_servers():
    servers = []
    with open('peering.json') as server_file:
        peering_json = json.load(server_file)
        try:
            # Check if file is ok
            servers = peering_json['peers']
        except Exception as e:
            print("The file peering.json contains erroneous data...")
            return None

    return servers

def select_leader():
    leader_index = np.random.randint(0, len(servers))
    return servers[leader_index]


def change_leader(proposed_leader):
    if proposed_leader != id_leader:
        id_leader = proposed_leader

servers = get_servers()
complete = False
id_leader = None

while not complete:
    timestep += 1
    state = readout_state()
    if id_leader is None:
        # Randomly select a server
        id_leader = select_leader()
    # Try replicate the action
    state_dict = {}
    state_dict['state'] = state
    state_decided = send_post(id_leader, 'decide_on_state', state_dict, TIMEOUT=0.075)

    # Check if no answer from the server
    if state_decider is None:
        # Set leader to None
        id_leader = None
        continue
    # Check if leader has changed
    change_leader(state_decided.json()['leader'])
    if not state_decided.json()['status']:
        # Consensus failed on State
        continue

    # Check the action that the leader will try to replicate
    action = send_post(id_leader, 'sample_next_action', {}, TIMEOUT=0.075)
    if action is None:
        # Leader maybe crashed...
        id_leader = None
        continue
    # check if action is None, i.e it means consensus is done
    change_leader(action.json()['leader'])
    if action.json()['action'] is None:
        complete = True
        continue

    action_dict = {}
    action_dict['action'] = action.json()['action']
    # Ask to leader to replicate this action
    action_decided = send_post(id_leader, 'decide_on_action', action_dict, TIMEOUT=0.075)
    if action_decided is None:
        id_leader = None
        timestep -= 1
        continue

    change_leader(action_decided.json()['leader'])
    if action_decided.json()['status']:
        execute_action(action.json()['action'])
    else:
        timestep -= 1

if complete:
    print("Success!")
else:
    print("Fail!")