#! /usr/bin/env python
# coding: utf-8
import argparse
import sys
import json
from flask import Flask, request, jsonify, redirect
import logging
from Raft.Server.raft import Raft
from Raft.Server.state import State
from Raft.Server.computers import *
import pickle


actions = pickle.load(open("data/actions.pickle", "rb"))
states = pickle.load(open("data/states.pickle", "rb"))

raft = None

app = Flask(__name__)
# disable flask logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

#garde
@app.route('/vote_request', methods=['POST'])
def vote_request():
    """
    Rules:  - Reply false if term < currentTerm
            - If votedFor is null or candidateId, and candidate’s log is at
              least as up-to-date as receiver’s log, grant vote
    """
    request_json = request.json
    print("Recois un vote request: {}".format(request_json))
    return jsonify(raft.decide_vote(request_json))

@app.route('/heartbeat', methods=['POST'])
def get_heartbeat():
    return jsonify(raft.process_heartbeat(request.json))

#garde
@app.route('/decide_on_state', methods=['POST'])
def decide_on_state():

    if raft.state is State.FOLLOWER:
        leader_id = raft.votedFor
        if leader_id is None:
            return error_no_leader_soft()

        print('DECIDE ON STATE REDIRECTION TO '.format(leader_id['port']))
        return redirect("http://{}:{}/decide_on_state"\
                         .format(leader_id['host'],\
                                 leader_id['port']),\
                         code=307)
    elif raft.state is State.CANDIDATE:
        return error_no_leader_soft()
    else:
        print('CHECK 1')
        asw = raft.state_consensus(request.json)
        response = {}
        response['host'] = raft.id['host']
        response['port'] = raft.id['port']
        response['status'] = asw['status']
        return jsonify(response)

@app.route('/acceptable_state', methods=['POST'])
def acceptable_state():
    return jsonify(raft.process_acceptable_state(request.json))

@app.route('/deliver_state', methods=['POST'])
def deliver_state():
    return jsonify(raft.process_deliver_state(request.json))

@app.route('/what_to_do', methods=['POST'])
def what_to_do():
    msg = request.json
    if msg['term'] >= raft.currentTerm:
        action = raft.fc.sample_next_action()
        print('TEST ACTION: {}'.format(action))
        asw = {'asw': True, 'action': action}
        return jsonify(asw)
    else:
        print('CHECK ERROR TERM!!!!!!!!!!!!!!')
        asw = {'asw': False}
        return jsonify(asw)



#garde
@app.route('/excute_action', methods= ['POST'])
def excute_action():
    msg = request.json

    """
    if msg['term'] >= raft.currentTerm:
        action = msg.pop('term')
        raft.fc.deliver_action(msg)
        asw = {'asw': True}
        return jsonify(asw)
    else:
        asw = {'asw': False}
        return jsonify(asw)
    """
    action = msg.pop('term')
    raft.fc.deliver_action(msg)
    asw = {'asw': True}
    return jsonify(asw)

#garde
@app.route('/action_consensus', methods= ['POST'])
def action_consensus():

    if raft.state is State.FOLLOWER:
        leader_id = raft.votedFor
        if leader_id is None:
            return error_no_leader()
        print('ACTION_CONSENSUS REDIRECTION TO '.format(leader_id['port']))
        return redirect("http://{}:{}/action_consensus"\
                         .format(leader_id['host'],\
                                 leader_id['port']),\
                         code=307)
    elif raft.state is State.CANDIDATE:
        return error_no_leader_soft()
    else:

        print('hello_1')
        response = raft.process_action_consensus(request.json)
        print('hello_2')
        response['host'] = raft.id['host']
        response['port'] = raft.id['port']
        print('-----------------------------')
        print(response)
        return jsonify(response)



@app.route('/decide_on_action', methods=['POST'])
def decide_on_action():
    if raft.state is State.FOLLOWER:
        leader_id = raft.votedFor
        if leader_id is None:
            return error_no_leader()
        return redirect("http://{}:{}/decide_on_action"\
                         .format(leader_id['host'],\
                                 leader_id['port']),\
                         code=307)
    elif raft.state is State.CANDIDATE:
        return error_no_leader()
    else:
        response = {}
        response['leader'] = raft.id
        response['status'] = raft.process_decide_on_command(request.json)
        return jsonify(response)

@app.route('/acceptable_action', methods=['POST'])
def acceptable_action():
    return jsonify(raft.process_acceptable_action(request.json))

@app.route('/next_handle_stage', methods=['POST'])
def decide_on_handle_stage():
    if raft.state is State.FOLLOWER:
        leader_id = raft.votedFor
        if leader_id is None:
            return error_no_leader()
        return redirect("http://{}:{}/decide_on_action"\
                         .format(leader_id['host'],\
                                 leader_id['port']),\
                         code=307)
    elif raft.state is State.CANDIDATE:
        return error_no_leader()
    else:
        response = {}
        response['leader'] = raft.id
        response['status'] = raft.process_decide_on_command(request.json)
        return jsonify(response)

@app.route('/deliver_handle_stage', methods=['POST'])
def deliver_handle_stage():
    return jsonify(raft.process_deliver_handle_stage(request.json))

@app.route('/sample_next_action', methods=['POST'])
def sample_next_action():
    if raft.state is State.FOLLOWER:
        leader_id = raft.votedFor
        if leader_id is None:
            return error_no_leader(action=True)
        return redirect("http://{}:{}/sample_next_action"\
                         .format(leader_id['host'],\
                                 leader_id['port']),\
                         code=307)
    elif raft.state is State.CANDIDATE:
        return error_no_leader(action=True)
    else:
        response = {}
        response['leader'] = raft.id
        response['action'] = raft.process_sample_next_action()
        return jsonify(response)


def error_no_leader(action=False):
    response = {}
    response['leader'] = None
    response['status'] = False
    if action:
        response['action'] = -1
    print('CHECK ERROR NO LEADER =========')
    return jsonify(response)

def error_no_leader_soft(action=False):
    response = {}
    response['host'] = None
    if action:
        response['action'] = -1
    print('CHECK ERROR NO LEADER SOFT =========')
    return jsonify(response)

def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--flight-computers-type", type=int, default=0, help="The type of flight computers (Normal=0 or Random=1). (default: 0)")
    parser.add_argument('--type', type=int, default=-1, help="Specifiy the type of bad computer to create")
    parser.add_argument("--port", type=int, default=8000, help="The port of the server (default: 8000).")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="The IP addresses of the server (default: localhost)")
    return parser.parse_known_args()

def get_peers(raft_id):
    peers = []
    with open('peering.json') as peers_file:
        peering_json = json.load(peers_file)
        try:
            # Check if file is ok
            peers = peering_json['peers']
            # Try to remove its own raft_id in peers
            peers.remove(raft_id)
        except Exception as e:
            print("The file peering.json contains erroneous data...")
            return None

    return peers

if __name__ == '__main__':
    (arguments, _) = parse_arguments()
    # Initialise the raft id
    raft_id = {'host': arguments.host, 'port': arguments.port}
    print("Starting to run the raft server http://{}:{}/".format(raft_id['host'], raft_id['port']))
    # Get the peers of the raft
    peers = get_peers(raft_id)
    if peers is None:
        sys.exit()
    # Initialise the flight computers and the raft. Then start the raft
    fc = None
    if arguments.type > -1:
        fc = allocate_specific_flight_computer(states[0], arguments.type)
    else:
        if arguments.flight_computers_type == 0:
            fc = FlightComputer(states[0])
        else:
            fc = allocate_random_flight_computer(states[0])
    print(fc)
    raft = Raft(fc, raft_id, peers)
    raft.start_raft()
    print('Start a new {} flight computer'.format(raft.fc.type))
    # Run Flask app
    app.run(debug=False, host=arguments.host, port=arguments.port)
