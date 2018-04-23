import hashlib
import json
from time import time
from urllib.parse import urlparse
import copy
import random


class Blockchain:
    def __init__(self, blockchain_id):
        self.blockchain_id = blockchain_id
        self.hardness = 4
        self.current_transactions = []
        self.chain = []
        self.nodes = set()
        
        # Create the genesis block
        self.new_block(previous_hash='1', proof=100)
    
    def register_node(self, address):
        """
        Add a new node to the list of nodes

        :param address: Address of node. Eg. 'http://192.168.0.5:5000'
        """
        
        parsed_url = urlparse(address)
        if parsed_url.netloc:
            self.nodes.add(parsed_url.netloc)
        elif parsed_url.path:
            # Accepts an URL without scheme like '192.168.0.5:5000'.
            self.nodes.add(parsed_url.path)
        else:
            raise ValueError('Invalid URL')
    
    def valid_chain(self, chain):
        """
        Determine if a given blockchain is valid

        :param chain: A blockchain
        :return: True if valid, False if not
        """
        
        last_block = chain[0]
        current_index = 1
        
        while current_index < len(chain):
            block = chain[current_index]
            # print(f'{last_block}')
            # print(f'{block}')
            # print("\n-----------\n")
            # Check that the hash of the block is correct
            if block['previous_hash'] != self.hash(last_block):
                return False
            
            # Check that the Proof of Work is correct
            if not self.valid_proof(last_block['proof'], block['proof'], block['previous_hash']):
                return False
            
            last_block = block
            current_index += 1
        
        return True
    
    def resolve_conflicts(self, all_chains):
        """
        This is our consensus algorithm, it resolves conflicts
        by replacing our chain with the longest one in the network.

        :return: True if our chain was replaced, False if not
        """
        
        new_chain = None
        all_chains_lengths = set([len(chain) for chain in all_chains])
        
        # if they are all of the same lengths, pick the first one that finished early
        # to simulate propagation into the network
        if len(all_chains_lengths) == 1:
            min_time = all_chains[0]['chain'][-1]['timestamp']
            min_time_index = 0
            for i in range(len(all_chains)):
                chain = all_chains[i]['chain']
                if chain[-1]['timestamp'] < min_time:
                    min_time = chain[-1]['timestamp']
                    min_time_index = i
            new_chain = all_chains[min_time_index]
        else:
            # We're only looking for chains longer than ours
            max_length = len(self.chain)
            
            # Grab and verify the chains from all the nodes in our network
            for chain_obj in all_chains:
                chain = chain_obj['chain']
                length = len(chain)
                
                # Check if the length is longer and the chain is valid
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain_obj
        
        # Replace our chain if we discovered a new, valid chain longer than ours
        if new_chain and new_chain['blockchain_id'] != self.blockchain_id:
            self.chain = copy.deepcopy(new_chain['chain'])
            return True
        
        return False
    
    def new_block(self, proof, previous_hash, node_identifier=None):
        """
        Create a new Block in the Blockchain

        :param proof: The proof given by the Proof of Work algorithm
        :param previous_hash: Hash of previous Block
        :return: New Block
        """
        
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
            'node_identifier': node_identifier
        }
        
        # Reset the current list of transactions
        self.current_transactions = []
        
        self.chain.append(block)
        return block
    
    def new_transaction(self, sender, recipient, amount):
        """
        Creates a new transaction to go into the next mined Block

        :param sender: Address of the Sender
        :param recipient: Address of the Recipient
        :param amount: Amount
        :return: The index of the Block that will hold this transaction
        """
        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        })
        
        return self.last_block['index'] + 1
    
    @property
    def last_block(self):
        return self.chain[-1]
    
    @staticmethod
    def hash(block):
        """
        Creates a SHA-256 hash of a Block

        :param block: Block
        """
        
        # We must make sure that the Dictionary is Ordered, or we'll have inconsistent hashes
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()
    
    def proof_of_work(self, last_block):
        """
        Simple Proof of Work Algorithm:

         - Find a number p' such that hash(pp') contains leading 4 zeroes
         - Where p is the previous proof, and p' is the new proof

        :param last_block: <dict> last Block
        :return: <int>
        """
        
        last_proof = last_block['proof']
        last_hash = self.hash(last_block)
        
        proof = random.randint(0, 2 ** 32)
        while self.valid_proof(last_proof, proof, last_hash) is False:
            proof += random.randint(0, 2 ** 32)
        
        return proof
    
    def valid_proof(self, last_proof, proof, last_hash):
        """
        Validates the Proof

        :param last_proof: <int> Previous Proof
        :param proof: <int> Current Proof
        :param last_hash: <str> The hash of the Previous Block
        :return: <bool> True if correct, False if not.

        """
        
        guess = f'{last_proof}{proof}{last_hash}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        
        hardness_string = ""
        for i in range(0, self.hardness):
            hardness_string += "0"
        
        return guess_hash[:self.hardness] == hardness_string
