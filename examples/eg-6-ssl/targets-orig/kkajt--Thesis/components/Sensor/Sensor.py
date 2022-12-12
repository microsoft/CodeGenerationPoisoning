import socket
import sys
import json
import pickle
import os
import codecs
from shamir_id_sig.lib.Device import Device
from OpenSSL import crypto
from certs_handling_sensor import *
import ssl
from oscrypto import asymmetric
from random import random, seed
import time
from asn1crypto import pem
from certvalidator import CertificateValidator, ValidationContext
import shutil
import os

class Sensor():

    HOST = ''	# Symbolic name meaning all available interfaces
    PORT = 8888	# Arbitrary non-privileged port
    SOCKET_BUFFER_SIZE = 4096
    state = 0
    # state - 1 when sensor is waiting for ID key, 2 when such is installed but there's no trust anchor, 
    # 3 - has trust anchor but not client certificate,  4 - has all the keys and certificates
    TRUST_ANCHOR_PATH = None
    TRUST_ANCHOR_PATH_TMP = None
    ID_PRIV_KEY = None
    ID_PUB_KEY = None
    PKI_CERT = None
    PKI_PRIV_KEY = None
    PKI_PUB_KEY = None
    ORG_NAME = None
    CA_BUNDLE_PATH = None
    CA_BUNDLE_PATH_TEMP = None
    PKI_CERT_TEMP = None


    def __init__(self, host = '', port = 8888, 
        ID_PUB_KEY = './certs/ID/id_pub.pem', ID_PRIV_KEY = './certs/ID/id_priv.key',
        TRUST_ANCHOR_PATH = './certs/anchor/root-ca.crt', PKI_CERT = './certs/PKI/sensor_cert.crt',
        PKI_PRIV_KEY = './certs/PKI/sensor_key_priv.key', ID = "", ORG_NAME = 'Thesis_Producent',
        PKI_PUB_KEY = './certs/PKI/sensor_key_pub.pkey', CA_BUNDLE_PATH = './certs/PKI/signing-ca.ca-bundle',
        CA_BUNDLE_PATH_TEMP = './certs/PKI/signing-ca-temp.ca-bundle',
        PKI_CERT_TEMP = './certs/PKI/sensor_cert-temp.crt',
        TRUST_ANCHOR_PATH_TMP = './certs/anchor/root-ca-temp.crt'):
        self.HOST = host
        self.PORT = port
        self.ID = ID
        self.ID_PRIV_KEY = ID_PRIV_KEY
        self.ID_PUB_KEY = ID_PUB_KEY
        self.TRUST_ANCHOR_PATH = TRUST_ANCHOR_PATH
        self.TRUST_ANCHOR_PATH_TMP = TRUST_ANCHOR_PATH_TMP
        self.PKI_CERT = PKI_CERT
        self.PKI_PRIV_KEY = PKI_PRIV_KEY
        self.state = 1
        self.device = Device()
        self.ORG_NAME = ORG_NAME
        self.PKI_PUB_KEY = PKI_PUB_KEY
        self.CA_BUNDLE_PATH = CA_BUNDLE_PATH
        self.CA_BUNDLE_PATH_TEMP = CA_BUNDLE_PATH_TEMP
        self.PKI_CERT_TEMP = PKI_CERT_TEMP

        if os.path.exists(self.ID_PRIV_KEY) and os.path.exists(self.ID_PUB_KEY):
            pub_key, priv_key, dev_id = self.restore_id_keys()
            self.set_sensor_id_key(pub_key, priv_key, dev_id)
            self.state = 2
            if os.path.exists(self.TRUST_ANCHOR_PATH):
                self.state = 3
                if os.path.exists(self.PKI_CERT) and os.path.exists(self.PKI_PRIV_KEY):
                    self.state = 4
        print("Sensor started.")
        print("Initial state: "+ str(self.state))

    def create_socket(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print('Socket created')

        try:
            s.bind((self.HOST, self.PORT))
        except socket.error:
            print('Bind failed.')
            sys.exit()
            
        print('Socket bind complete.')
        return s
    
    def listen_on_socket(self, s):
        s.listen(10)
        print('Socket now listening on ' + str(self.HOST) + ":" + str(self.PORT))
        while True:
            try:
                # wait to accept a connection - blocking call
                print("Waiting for connection...")
                conn, addr = s.accept()
                print('Connected with ' + addr[0] + ':' + str(addr[1]))
                
                msg = {'msg': "SERVERHELLO", "id": self.ID, "state" : self.state} 
                conn.sendall(pickle.dumps(msg))
                rsp = self.parse_rsp(conn.recv(self.SOCKET_BUFFER_SIZE))
                print("Got server request.")

                # Initialise proper procedure according to the API
                if rsp['msg'] == 'INSTALL_TRUST_ANCHOR':
                    self.install_trust_anchor_init(conn)
                elif rsp['msg'] == 'GETCSR':
                    self.send_csr(conn)
                elif rsp['msg'] == 'INSTALL_CERT':
                    self.install_pki_init(conn)
                elif rsp['msg'] == 'TLS_CONNECTION':
                    self.perform_tls_connection_two_way_vrfy(conn)
                elif rsp['msg'] == 'CLOSE':
                    print("Client requested closing the connection.")
                    conn.close()
                    print("Connection closed.")
                else:
                    print("Unknown command. Connection closed.")
                    conn.close()
            except KeyboardInterrupt:
                print("\nExiting")
                conn.close()
                self.quit_program()
            except Exception as ex:
                print(ex)
                print("Aborting connection...")
                conn.close()
    
    def quit_program(self):
        raise SystemExit

    def send_csr(self, conn):
        print("Terminal requested CSR.\nInitializing the procedure...")
        if self.state == 1:
            print("Can't install in PKI. Need to add ID private key first.")
            self.send_error_msg(conn)
            conn.close()
            return
        if self.state == 2:
            print("Can't install in PKI. Need to add trust anchor first.")
            self.send_error_msg(conn)
            conn.close()
            return 

        msg = {'msg': 'OK'}
        self.send_json_message(msg, conn)
        conn = self.perform_tls_connection_client_verify(conn)
        rsp = self.parse_rsp(conn.recv(self.SOCKET_BUFFER_SIZE))
        if rsp['msg'] == 'CERT_DATA':
            cert_data = rsp['certdata']
        if self.state == 3:
            req = self.gen_cert_request_idb(self.ID)
            self.send_cert_request(req, conn)
        elif self.state == 4:
            req = self.gen_cert_request_rsa(self.ID) 
            self.send_cert_request(req, conn, idb = False)
        rsp = self.parse_rsp(conn.recv(self.SOCKET_BUFFER_SIZE))
        if rsp['msg'] == 'SUCCESS':
            print("Terminal received CSR.")
        else:
            print("Terminal had issues receiving CSR. Try again.")
        conn.close()

    def read_priv_key_from_file(self, filename):
        try:
            with open(filename, 'rt') as f:
                st_key = f.read()
            key = crypto.load_privatekey(crypto.FILETYPE_PEM, st_key)
            return key
        except:
            print("Can't read the keys.")
            raise Exception()

    def read_pub_key_from_file(self, filename):
        try:
            with open(filename, 'rt') as f:
                st_key = f.read()
            key = crypto.load_publickey(crypto.FILETYPE_PEM, st_key)
            return key
        except Exception as ex:
            print(ex)
            print("Can't read the keys.")
            raise Exception()

    def gen_cert_request_rsa(self, cname):
        print("Generating certificate signing request with RSA signature...")
        priv_key = self.read_priv_key_from_file(self.PKI_PRIV_KEY)
        pub_key = self.read_pub_key_from_file(self.PKI_PUB_KEY)
        req = create_csr_rsa(pub_key, priv_key, O=self.ORG_NAME, CN=cname)
        print("Generation completed.")
        return req
    
    def gen_cert_request_idb(self, cname):
        print("Generating certificate signing request with ID-based signature...")
        pub_key_rsa, priv_key_rsa = create_key_pair('rsa', 1024)
        req = create_csr_idb(self.device.priv_key, self.device.pub_key, pub_key_rsa, self.ORG_NAME, cname)
        with open(self.PKI_PRIV_KEY, 'wb+') as f: 
            f.write(asymmetric.dump_private_key(priv_key_rsa, None))
        with open(self.PKI_PUB_KEY, 'wb+') as f: 
            f.write(asymmetric.dump_public_key(pub_key_rsa))
        print("Generation completed.")
        return req

    def install_pki_init(self, conn):
        print("Client requested pki installation.\nInitializing the procedure...")
        if self.state == 1:
            print("Can't install in PKI. Need to add ID private key first.")
            self.send_error_msg(conn)
            conn.close()
            return
        if self.state == 2:
            print("Can't install in PKI. Need to add trust anchor first.")
            self.send_error_msg(conn)
            conn.close()
            return 

        msg = {'msg': 'OK'}
        self.send_json_message(msg, conn)

        conn = self.perform_tls_connection_client_verify(conn)
        rsp = self.parse_rsp(conn.recv(self.SOCKET_BUFFER_SIZE))

        if rsp['msg'] == 'CA-BUNDLE':
            print("Receiving CA-bundle...")
            try:
                self.receive_file_over_socket(conn, self.CA_BUNDLE_PATH_TEMP)
                if self.verify_ca_bundle(self.TRUST_ANCHOR_PATH, self.CA_BUNDLE_PATH_TEMP):
                    self.replace_file(self.CA_BUNDLE_PATH, self.CA_BUNDLE_PATH_TEMP)
                else:
                    print("Closing connection...")
                    self.send_error_msg(conn)
                    self.delete_temp(self.CA_BUNDLE_PATH_TEMP)
                    conn.close()
            except Exception as ex:
                print(ex)
                msg = {'msg': 'ERROR'}
                self.send_json_message(msg, conn)
                conn.close()
            msg = {'msg': 'SUCCESS'}
            self.send_json_message(msg, conn)
            rsp = self.parse_rsp(conn.recv(self.SOCKET_BUFFER_SIZE))
            if rsp['msg'] == 'CERTIFICATE':
                print("Receiving the certificate...")
                rsp = conn.recv(self.SOCKET_BUFFER_SIZE)
                cert = crypto.load_certificate(crypto.FILETYPE_PEM, rsp)
                print("Certificate successfully received.")
                if self.install_pki_cert(cert):
                    msg = {"msg": "SUCCESS"}
                    self.send_json_message(msg, conn)
                else:
                    self.send_error_msg(conn)
                conn.close()
        else:
            print("There was an error received from RA. Aborting operation...")
            conn.close()
            

    def install_pki_cert(self, cert):
        print("Installing PKI cert...")
        pub_key = self.read_pub_key_from_file(self.PKI_PUB_KEY)
        with open(self.PKI_CERT_TEMP, 'wb+') as f: 
                f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
        if self.verify_cert(cert, pub_key):
            with open(self.PKI_CERT, 'wb+') as f: 
                f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
            print("Certificate saved.")
            self.state = 4
            self.delete_temp(self.PKI_CERT_TEMP)
            return True
        else:
            print("Certificate verification fail. Dropping the certificate.")
            self.delete_temp(self.PKI_CERT_TEMP)
            return False
    
    def delete_temp(self, path):
        if os.path.exists(path):
            os.remove(path)

    def verify_cert(self, cert, pub_key):

        verified = True
        cert_pub_key = cert.get_pubkey()

        if not self.verify_ca_bundle(self.TRUST_ANCHOR_PATH, self.CA_BUNDLE_PATH, end_entity=self.PKI_CERT_TEMP):
            print("Certificate verification fail: Certificate verification against certificate chain failed.")
            verified = False
        if cert.has_expired():
            print("Ceritficate verification fail: Certificate has expired.")
            verified = False

        if cert_pub_key.to_cryptography_key().public_numbers().n != pub_key.to_cryptography_key().public_numbers().n \
            or cert_pub_key.to_cryptography_key().public_numbers().e != pub_key.to_cryptography_key().public_numbers().e:
            print("Ceritficate verification fail: public keys doesn't match.")
            verified = False

        if self.ID != cert.get_subject().commonName:
            print("Ceritficate verification fail: common_name value does not match.")
            verified = False
        return verified

    def replace_file(self, file_to_be_replaced, file_replacing):
        os.replace(file_replacing, file_to_be_replaced)
        
    def send_cert_request(self, req, conn, idb = True):
        print("Sending certificate signing request...")
        if idb:
            req_pem = pem_armor_csr(req)
        else:
            req_pem = crypto.dump_certificate_request(crypto.FILETYPE_PEM, req)
        msg = {'msg': "CERT REQUEST"}
        self.send_json_message(msg, conn)
        time.sleep(0.25)
        conn.sendall(req_pem)
        print("Certificate signing request sent.")

    def install_trust_anchor_init(self, conn):
        print("Client requested trust anchor installation.\nInitializing the procedure...")
        if self.state == 1:
            print("Can't install trust anchor. Device has no ID-based private key installed.")
            msg = {'msg': 'FAIL'}
            self.send_json_message(msg, conn)
            conn.close()
            return
        msg = {'msg': 'OK'}
        print("Waiting for trust anchor from server...")
        self.send_json_message(msg, conn)
        if self.state == 2:
            # if the device has not trust anchor installed already
            self.install_trust_anchor_first(conn)
        elif self.state == 3 or self.state == 4:
            # if the device has trust anchor already installed
            self.install_trust_anchor_next(conn)            

    def install_trust_anchor_next(self, conn):
        try:
            self.receive_file_over_socket(conn, self.TRUST_ANCHOR_PATH_TMP)
        except Exception as ex:
            print(ex)
            print("Received empty file.")
            msg = {'msg': 'ERROR'}
            self.send_json_message(msg, conn)
            conn.close()
        if self.verify_trust_anchor(self.TRUST_ANCHOR_PATH, self.TRUST_ANCHOR_PATH_TMP):
            self.replace_file(self.TRUST_ANCHOR_PATH, self.TRUST_ANCHOR_PATH_TMP)
            self.delete_temp(self.TRUST_ANCHOR_PATH_TMP)
            msg = {'msg': 'OK', 'id': self.ID}
            self.state = 3
            time.sleep(0.5)
            self.send_json_message(msg, conn)
            conn.close()
        else:
            msg = {'msg': 'VERIFICATION_FAILURE'}
            time.sleep(0.5)
            self.send_json_message(msg, conn)
            conn.close()

    def verify_trust_anchor(self, old_trust_anchor_path, new_trust_anchor_path):
        st_cert = open(new_trust_anchor_path, 'rt').read()
        new_trust_anchor = crypto.load_certificate(crypto.FILETYPE_PEM, st_cert)

        st_cert = open(old_trust_anchor_path, 'rt').read()
        old_trust_anchor = crypto.load_certificate(crypto.FILETYPE_PEM, st_cert)

        # verify validity of new trust anchor
        try:
            cert_store = crypto.X509Store()
            cert_store.add_cert(new_trust_anchor)
            store_ctx = crypto.X509StoreContext(cert_store, new_trust_anchor)
            store_ctx.verify_certificate()
        except Exception as ex:
            print(ex)
            return False

        # verify public keys are same with old trust anchor
        if crypto.dump_publickey(crypto.FILETYPE_PEM, new_trust_anchor.get_pubkey()) == crypto.dump_publickey(crypto.FILETYPE_PEM, old_trust_anchor.get_pubkey()):
            return True
        else:
            return False

    def install_trust_anchor_first(self, conn):
        try:
            self.receive_file_over_socket(conn, self.TRUST_ANCHOR_PATH)
        except Exception as ex:
            print(ex)
            print("Received empty file.")
            msg = {'msg': 'ERROR'}
            self.send_json_message(msg, conn)
            conn.close()
        msg = {'msg': 'OK', 'id': self.ID}
        self.state = 3
        time.sleep(0.5)
        self.send_json_message(msg, conn)
        conn.close()
    
    def sign_msg(self, msg):
        return self.device.sign(msg)

    def send_json_message(self, msg, conn):
        conn.sendall(pickle.dumps(msg))

    def set_sensor_id_key(self, pub_key, priv_key, dev_id):
        self.device.pub_key = pub_key
        self.device.priv_key = priv_key
        self.ID = dev_id
        print("Device ID: " + self.ID)
    
    def restore_id_keys(self):
        print("Restoring ID keys from file...")
        with open(self.ID_PRIV_KEY, 'rb') as key_file:
            b64 = key_file.read()
            priv_key = pickle.loads(codecs.decode(b64, "base64"))
        with open(self.ID_PUB_KEY, 'rb') as key_file:
            b64 = key_file.read()
            pub_key_data = pickle.loads(codecs.decode(b64, "base64"))
            pub_key = pub_key_data[0]
            dev_id = pub_key_data[1]
        print("Restoring ID keys finished.")
        return pub_key, priv_key, dev_id

    def parse_rsp(self, response):
        return pickle.loads(response) # deserialization

    def perform_tls_connection_two_way_vrfy(self, conn):
        print("Terminal requested secured connection.\nInitializing TLS socket...")
        if self.state != 4:
            print("Sensor has no TLS certificate yet.")
            self.send_error_msg(conn)
            conn.close()
        msg = {'msg': 'OK'}
        self.send_json_message(msg, conn)
        tls_conn = self.tls_wrap_two_way_vrf(conn)
        print("TLS connection established")
        msg = {'msg': 'SUCCESS'}
        self.send_json_message(msg, tls_conn)
        self.send_secrets(tls_conn)
        
    def send_secrets(self, tls_conn):
        try:
            while(True):
                secret = random()
                msg = {'secret': secret}
                print("Sending secret: " + str(secret))
                self.send_json_message(msg, tls_conn)
                time.sleep(1)
        except BrokenPipeError:
            print("Terminal closed the connection. Exiting connection.")
            tls_conn.close()

    def tls_wrap_two_way_vrf(self, conn):
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(self.PKI_CERT, self.PKI_PRIV_KEY)
        return ssl.wrap_socket(conn,
                server_side=True,
                certfile=self.PKI_CERT,
                keyfile=self.PKI_PRIV_KEY,
                ca_certs=self.CA_BUNDLE_PATH
                )    
    
    def perform_tls_connection_client_verify(self, conn):
        return ssl.wrap_socket(conn,
                    ca_certs=self.TRUST_ANCHOR_PATH,
                    cert_reqs=ssl.CERT_REQUIRED,
                    )

    def receive_file_over_socket(self, s, filename):
        print("Receiving file and saving to " + filename)
        filesize = s.recv(32)
        
        filesize = int(filesize.decode(), 2)
        with open(filename, 'wb+') as f:
            chunksize = 4096
            while filesize > 0:
                if filesize < chunksize:
                    chunksize = filesize
                data = s.recv(chunksize)
                f.write(data)
                filesize -= len(data)
        print("Received file successfully.")
    
    def send_error_msg(self, conn, err_msg = "ERROR"):
        msg = {"msg": err_msg}
        self.send_json_message(msg, conn)

    def verify_ca_bundle(self, trust_anchor_file, chain_file, end_entity = None):
        end_entity_cert = None
        if end_entity is not None:
            with open(end_entity, 'rb') as f:
                type_name, headers, der_bytes = pem.unarmor(f.read())
                end_entity_cert = der_bytes
        intermediates = []
        with open(chain_file, 'rb') as f:
            for type_name, headers, der_bytes in pem.unarmor(f.read(), multiple=True):
                if end_entity_cert is None:
                    end_entity_cert = der_bytes
                else:
                    intermediates.append(der_bytes)
        
        trust_roots = []
        with open(trust_anchor_file, 'rb') as f:
            for _, _, der_bytes in pem.unarmor(f.read(), multiple=True):
                trust_roots.append(der_bytes)
        context = ValidationContext(trust_roots=trust_roots)
        
        try:
            validator = CertificateValidator(end_entity_cert, intermediate_certs=intermediates, validation_context=context)
            validator.validate_usage(set([]))
            return True
        except Exception as ex:
            print(ex)
            print("Certificate chain verification failed.")
            return False
        
