from flask import Flask, request, render_template, redirect, url_for, session, jsonify, flash
from hashlib import sha256
import json
import time
import requests
from blockchain import Blockchain,Block, Transaction
from collections import OrderedDict
import binascii
import Crypto
import Crypto.Random
from Crypto.Hash import SHA
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
import hashlib
# from urllib.parse import urlparse
from uuid import uuid4
from flask_ngrok import run_with_ngrok
from flask_cors import CORS

app=Flask(__name__)
app.secret_key = 'Amex Hacakthon 2020'
CORS(app)
run_with_ngrok(app)

logininfo = Blockchain()
logininfo.create_genesis_block()
servicesinfo = Blockchain()
servicesinfo.create_genesis_block()
transactioninfo = Blockchain()
transactioninfo.create_genesis_block()
peers=set()

@app.route('/analytics', methods=['GET'])
def data_analytics():
    return render_template('analytics.html')

@app.route('/', methods=['GET'])
def index():
    if not 'logged_in' in session:
        session['logged_in']=False
    if session['logged_in']:
        return redirect(url_for('user_dashboard'))
    return render_template('index.html')

@app.route('/logout')
def logout_user():
    session.pop('data', None)
    session.pop('balance', None)
    session['logged_in']=False
    return redirect(url_for('index'))

@app.route('/about_us')
def about():
    return render_template('about_us.html')

@app.route('/join')
def join_network():
    return render_template('join.html')

@app.route('/profile')
def user_profile():
    return render_template('profile.html')

@app.route('/team')
def team_info():
    return render_template('team.html')

@app.route('/dashboard')
def user_dashboard():
    if not session['logged_in']:
        return redirect(url_for('index'))
    return render_template('dashboard.html', data=session['data'], serviceinfo=servicesinfo)

@app.route('/connect', methods=['GET', 'POST'])
def login_signup():
    if request.method=='GET':
        return render_template('connect.html')
    if request.method=='POST':
        if 'loginbtn' in request.form:
            username=request.form['username']
            password=request.form['pass']
            data={"username":username,"password":password}
            required_fields = ["username", "password"]
            for field in required_fields:
                if not data.get(field):
                    return "Invalid login data"
            for block in logininfo.chain:
                for transaction in block.transactions:
                    if(transaction['username']==username and transaction['password']==password):
                        session['logged_in']=True
                        session['data']=transaction
                        return redirect(url_for('user_dashboard'))
            return "Please Signup First"

        if 'signupbtn' in request.form:
            username=request.form['username']
            password=request.form['pass']
            user_type=request.form['type']
            name=request.form['name']
            data={"username":username,"password":password, "name": name, "type": user_type}
            required_fields = ["username", "password", "type" , "name"]
            for field in required_fields:
                if not data.get(field):
                    return "Invalid signup data"
            data["timestamp"] = time.ctime()
            random_gen = Crypto.Random.new().read
            private_key = RSA.generate(1024, random_gen)
            public_key = private_key.publickey()
            data["private_key"] = binascii.hexlify(private_key.exportKey(format='DER')).decode('ascii')
            data["public_key"] = binascii.hexlify(public_key.exportKey(format='DER')).decode('ascii')
            logininfo.add_new_transaction(data)
            session['logged_in']=True
            session['data']=data
            return redirect(url_for('mine_unconfirmed_transactions_l'))

@app.route('/mine_l', methods=['GET'])
def mine_unconfirmed_transactions_l():
    result = logininfo.mine()
    if not result:
        return "No transactions to mine (logininfo)"
    else:
        chain_length = len(logininfo.chain)
        # print(chain_length)
        consensus_l()
        # print(l(logininfo.chain))
        if chain_length == len(logininfo.chain):
            announce_new_block_l(logininfo.last_block)
        return redirect(url_for('user_dashboard'))

def consensus_l():
    global logininfo

    longest_chain = None
    current_len = len(logininfo.chain)

    for node in peers:
        response = requests.get('{}chain_l'.format(node))
        length = response.json()['length']
        chain = response.json()['chain']
        if length > current_len and Blockchain.check_chain_validity(chain):
            current_len = length
            longest_chain = chain

    if longest_chain:
        logininfo = longest_chain
        return True

    return False

def announce_new_block_l(block):
    for peer in peers:
        url = "{}add_block_l".format(peer)
        headers = {'Content-Type': "application/json"}
        requests.post(url,
                      data=json.dumps(block.__dict__, sort_keys=True),
                      headers=headers)

@app.route('/add_block_l', methods=['POST'])
def verify_and_add_block_l():
    block_data = request.get_json()
    block = Block(block_data["index"],
                  block_data["transactions"],
                  block_data["timestamp"],
                  block_data["previous_hash"],
                  block_data["nonce"])

    proof = block_data['hash']
    added = logininfo.add_block(block, proof)

    if not added:
        return "The block was discarded by the node", 400

    return "Block added to the chain", 201

@app.route('/add_service', methods=['POST'])
def new_service():
    name=request.form['name']
    amount=request.form['amount']
    service={'id':session['data']['username'],'company_name':session['data']['name'], 'name':name,'amount':amount, 'timestamp': time.ctime()}
    servicesinfo.add_new_transaction(service)
    return redirect(url_for('mine_unconfirmed_transactions_s'))
    # return render_template('home.html', data=session['data'], serviceinfo=servicesinfo)

@app.route('/mine_s', methods=['GET'])
def mine_unconfirmed_transactions_s():
    result = servicesinfo.mine()
    if not result:
        return "No transactions to mine"
    else:
        chain_length = len(servicesinfo.chain)
        # print(chain_length)
        consensus_s()
        # print(l(logininfo.chain))
        if chain_length == len(servicesinfo.chain):
            announce_new_block_s(servicesinfo.last_block)
        return redirect(url_for('user_dashboard'))

def consensus_s():
    global servicesinfo

    longest_chain = None
    current_len = len(servicesinfo.chain)

    for node in peers:
        response = requests.get('{}chain_s'.format(node))
        length = response.json()['length']
        chain = response.json()['chain']
        if length > current_len and Blockchain.check_chain_validity(chain):
            current_len = length
            longest_chain = chain

    if longest_chain:
        servicesinfo = longest_chain
        return True

    return False

def announce_new_block_s(block):
    for peer in peers:
        url = "{}add_block_s".format(peer)
        headers = {'Content-Type': "application/json"}
        requests.post(url,
                      data=json.dumps(block.__dict__, sort_keys=True),
                      headers=headers)

@app.route('/add_block_s', methods=['POST'])
def verify_and_add_block_s():
    block_data = request.get_json()
    block = Block(block_data["index"],
                  block_data["transactions"],
                  block_data["timestamp"],
                  block_data["previous_hash"],
                  block_data["nonce"])

    proof = block_data['hash']
    added = servicesinfo.add_block(block, proof)

    if not added:
        return "The block was discarded by the node", 400

    return "Block added to the chain", 201

@app.route('/buy_service/<idx>/<amount>')
def new_buy_service(idx,amount):
    print(session['balance'])
    print(amount)
    if(int(session['balance'])>=int(amount)):
        sender_address = session['data']['public_key']
        sender_private_key = session['data']['private_key']
        # print(sender_private_key)
        value = amount
        recipient_address = None
        for block in logininfo.chain:
            for transaction in block.transactions:
                if(transaction['username']==idx):
                    recipient_address = transaction['public_key']
                    # print(recipient_address)
                    break

        transaction = Transaction(sender_address, sender_private_key, recipient_address, value)

        response = {'transaction': transaction.to_dict(), 'signature': transaction.sign_transaction()}
        response['transaction']['sender_private_key'] = sender_private_key
        return render_template('payment.html', response=response)
    else:
        flash("You do not have sufficient wallet balance.")
        return redirect(url_for('user_dashboard'))

@app.route('/success', methods=['POST'])
def new_transaction():
    values = request.form
    # print(values)
    # Check that the required fields are in the POST'ed data
    required = ['sender_address', 'recipient_address', 'amount', 'signature']
    if not all(k in values for k in required):
        return 'Missing values', 400
    # Create a new Transaction
    transaction_result = transactioninfo.submit_transaction(values['sender_address'], values['recipient_address'], values['amount'], values['signature'])

    if transaction_result == False:
        response = {'message': 'Invalid Transaction!'}
        return jsonify(response), 406
    else:
        transaction = {'sender_address': values['sender_address'], 'recipient_address': values['recipient_address'], 'value': values['amount']}
        transactioninfo.add_new_transaction(transaction)
        announce_new_transaction_t(transaction)
        response = "Payment was Successful"
        return render_template('success.html')

def announce_new_block_t(block):
    for peer in peers:
        url = "{}add_block_t".format(peer)
        headers = {'Content-Type': "application/json"}
        requests.post(url,
                      data=json.dumps(block.__dict__, sort_keys=True),
                      headers=headers)

@app.route('/add_block_t', methods=['POST'])
def verify_and_add_block_t():
    block_data = request.get_json()
    block = Block(block_data["index"],
                  block_data["transactions"],
                  block_data["timestamp"],
                  block_data["previous_hash"],
                  block_data["nonce"])

    proof = block_data['hash']
    added = transactioninfo.add_block(block, proof)

    if not added:
        return "The block was discarded by the node", 400

    return "Block added to the chain", 201

@app.route('/add_transaction_t', methods=['POST'])
def add_transaction1_t():
    transaction_data = request.get_json()
    added = transactioninfo.add_new_transaction(transaction_data)
    # announce_new_transaction_t(transaction_data)

    if not added:
        return "The transaction was discarded by the node", 400

    return "Transaction added to the unconfirmed transactions", 201

def announce_new_transaction_t(block):
    for peer in peers:
        url = "{}add_transaction_t".format(peer)
        headers = {'Content-Type': "application/json"}
        requests.post(url,
                      data=json.dumps(block.__dict__, sort_keys=True),
                      headers=headers)

@app.route('/pending_tx_t')
def get_pending_tx_t():
    return json.dumps(transactioninfo.unconfirmed_transactions)

def consensus_t():
    global transactioninfo

    longest_chain = None
    current_len = len(transactioninfo.chain)

    for node in peers:
        response = requests.get('{}chain_t'.format(node))
        length = response.json()['length']
        chain = response.json()['chain']
        if length > current_len and Blockchain.check_chain_validity(chain):
            current_len = length
            longest_chain = chain

    if longest_chain:
        transactioninfo = longest_chain
        return True

    return False

@app.route('/mine_t', methods=['GET'])
def mine_unconfirmed_transactions_t():
    # mining rewards added
    if(len(transactioninfo.unconfirmed_transactions)!=0):
        transaction={'sender_address': "CHAIN.IT", 'recipient_address': session['data']['public_key'], 'value': 50}
        transactioninfo.add_new_transaction(transaction)
    result = transactioninfo.mine()
    if not result:
        return "No transactions to mine"
    else:
        chain_length = len(transactioninfo.chain)
        # print(chain_length)
        consensus_t()
        # print(l(logininfo.chain))
        if chain_length == len(transactioninfo.chain):
            announce_new_block_t(transactioninfo.last_block)
        # return render_template('home.html', data=session['data'], serviceinfo=servicesinfo)
        flash("Transactions successfully mined. Block #{} added.".format(chain_length))
        return redirect(url_for('user_dashboard'))

@app.route('/chain_l', methods=['GET'])
def get_chain_l():
    chain_data = []
    for block in logininfo.chain:
        chain_data.append(block.__dict__)
    return {"length": len(chain_data),"chain": chain_data,"peers": list(peers)}

@app.route('/chain_s', methods=['GET'])
def get_chain_s():
    chain_data = []
    for block in servicesinfo.chain:
        chain_data.append(block.__dict__)
    return {"length": len(chain_data),"chain": chain_data,"peers": list(peers)}

@app.route('/chain_t', methods=['GET'])
def get_chain_t():
    chain_data = []
    for block in transactioninfo.chain:
        chain_data.append(block.__dict__)
    return {"length": len(chain_data),"chain": chain_data,"peers": list(peers)}

@app.route('/get_balance', methods=['GET'])
def balance():
    amount=100
    amount_p=0
    for block in transactioninfo.chain:
        for transaction in block.transactions:
            if(transaction['sender_address']==session['data']['public_key']):
                amount = amount - int(transaction['value'])
            if(transaction['recipient_address']==session['data']['public_key']):
                amount = amount + int(transaction['value'])
    for transaction in transactioninfo.unconfirmed_transactions:
        if(transaction['sender_address']==session['data']['public_key']):
            amount_p = amount_p - int(transaction['value'])
        if(transaction['recipient_address']==session['data']['public_key']):
            amount_p = amount_p + int(transaction['value'])
    data={'amount': amount, 'amount_p': amount_p}
    session['balance']=amount
    # print(session['balance'])
    return data, 200

@app.route('/register_node', methods=['POST'])
def register_new_peers():
    node_address = request.get_json()["node_address"]
    if not node_address:
        return "Invalid data", 400
    for peer in peers:
        result = requests.post(peer+"add_peer", data=node_address)
    peers.add(node_address)
    response={"l":get_chain_l(),"s":get_chain_s(),"t":get_chain_t(), "peers": repr(peers)}
    return response

@app.route('/add_peer', methods=['POST'])
def add_new_peer():
    node_address = request.data
    # print(node_address)
    peers.add(node_address)
    return "True"

@app.route('/register_with', methods=['POST'])
def register_with_existing_node():
    # print(request.get_json())
    node_address = request.form["node_address"]
    if not node_address:
        return "Invalid data", 400

    data = {"node_address": request.host_url}
    headers = {'Content-Type': "application/json"}

    response2 = requests.post(node_address + "/register_node", data=json.dumps(data), headers=headers)
    response1 = eval(response2.content)
    response_peers = eval(response1['peers'])
    response={"l":response1['l'],"s":response1['s'],"t":response1['t']}

    if response2.status_code==200:
        global logininfo
        global servicesinfo
        global transactioninfo
        global peers
        chain_dump_l = response['l']['chain']
        chain_dump_s = response['s']['chain']
        chain_dump_t = response['t']['chain']
        logininfo, servicesinfo, transactioninfo = create_chain_from_dump(chain_dump_l, chain_dump_s, chain_dump_t)
        for peer in response_peers:
            if(peer!=request.host_url):
                peers.add(peer)
        peers.add(node_address+"/")
        # flash("Registration successful")
        return redirect(url_for('join_network'))
    else:
        return response1.content, response1.status_code


def create_chain_from_dump(chain_dump_l, chain_dump_s, chain_dump_t):
    generated_blockchain_l = Blockchain()
    generated_blockchain_l.create_genesis_block()
    for idx, block_data in enumerate(chain_dump_l):
        if idx == 0:
            continue  # skip genesis block
        block = Block(block_data["index"],
                      block_data["transactions"],
                      block_data["timestamp"],
                      block_data["previous_hash"],
                      block_data["nonce"])
        proof = block_data['hash']
        added = generated_blockchain_l.add_block(block, proof)
        if not added:
            raise Exception("The chain dump is tampered!!")
    generated_blockchain_s = Blockchain()
    generated_blockchain_s.create_genesis_block()
    for idx, block_data in enumerate(chain_dump_s):
        if idx == 0:
            continue  # skip genesis block
        block = Block(block_data["index"],
                      block_data["transactions"],
                      block_data["timestamp"],
                      block_data["previous_hash"],
                      block_data["nonce"])
        proof = block_data['hash']
        added = generated_blockchain_s.add_block(block, proof)
        if not added:
            raise Exception("The chain dump is tampered!!")
    generated_blockchain_t = Blockchain()
    generated_blockchain_t.create_genesis_block()
    for idx, block_data in enumerate(chain_dump_t):
        if idx == 0:
            continue  # skip genesis block
        block = Block(block_data["index"],
                      block_data["transactions"],
                      block_data["timestamp"],
                      block_data["previous_hash"],
                      block_data["nonce"])
        proof = block_data['hash']
        added = generated_blockchain_t.add_block(block, proof)
        if not added:
            raise Exception("The chain dump is tampered!!")
    return generated_blockchain_l,generated_blockchain_s,generated_blockchain_t

@app.route('/analytics1', methods=['GET'])
def count_service_smbwise():
    legend = "No of Services"
    labels = []
    for block in logininfo.chain:
        for transaction in block.transactions:
            if(transaction['type']=='smb'):
                labels.append(transaction['name'])
    values = [0]*len(labels)
    for block in servicesinfo.chain:
        for transaction in block.transactions:
            idx = labels.index(transaction['company_name']) 
            values[idx] = values[idx] + 1
    data = {'legend': legend, 'labels': labels, 'values': values}
    # print(data)
    return data, 200

@app.route('/analytics2', methods=['GET'])
def count_usertype():
    labels = ["Client", "SMB"]
    values = [0, 0]
    for block in logininfo.chain:
        for transaction in block.transactions:
            if(transaction['type']=='smb'):
                values[1] = values[1] + 1
            else:
                values[0] = values[0] + 1
    data = {'labels': labels, 'values': values}
    # print(data)
    return data, 200

if __name__ == '__main__':
    app.run(debug=True)