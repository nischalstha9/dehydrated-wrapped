#!/usr/bin/python3

import os
import subprocess
import argparse

from alpn_responder import ThreadedTCPServer, ThreadedTCPRequestHandler

class CertificateHandler:
    """
        Handler to generate certificate.
    """
    BASE_DIR=os.path.dirname(os.path.realpath(__file__))
    DOMAINS_FILE_PATH = 'domains.txt'
    CONFIG_FILE_PATH = 'config'
    CREATE_DOMAINS_FILE = True
    CREATE_CONFIG_FILE = True
    DOMAINS = []
    RAW_EXEC_ARGS=[]
    CA = "https://acme-staging-v02.api.letsencrypt.org/directory"

    def __init__(self, staging=False, domains=DOMAINS, domains_file=None, config_file=None, raw_args=None):
        self.CA = "https://acme-staging-v02.api.letsencrypt.org/directory" if staging \
            else "https://acme-v01.api.letsencrypt.org/directory"
        self.DOMAINS = domains
        if domains_file:
            self.DOMAINS_FILE_PATH = domains_file
            self.CREATE_DOMAINS_FILE = False
        if config_file:
            self.CONFIG_FILE_PATH = config_file
            self.CREATE_CONFIG_FILE = False
        if raw_args:
            self.RAW_EXEC_ARGS = raw_args

    def generate_config(self):
        try:
            os.environ['CA'] = self.CA
            if self.CREATE_DOMAINS_FILE:
                self.generate_domains_file()
            os.environ['DOMAINS_FILE_PATH'] = self.DOMAINS_FILE_PATH
            subprocess.run([f'{self.BASE_DIR}/envsubst', '-i', 'config.example', '-o', self.CONFIG_FILE_PATH])
        except:
            print("Error creating config file... Exitting...")
            exit(1)

    def generate_domains_file(self):
        try:
            if len(self.DOMAINS) > 0:
                with open(self.DOMAINS_FILE_PATH, "w") as file:
                    for domain in self.DOMAINS:
                        file.write(domain.strip() + "\n")
                        print("Domains file created successfully.")
            else:
                print("Error creating Domains file.")
                exit(1)
        except:
            print("Error creating domains file... Exitting...")
            exit(1)
    
    # def get_domains_file_path(self):
    #     if self.CREATE_DOMAINS_FILE:
    #         self.generate_domains_file()
    #     return self.DOMAINS_FILE_PATH

    def register(self):
        subprocess.run([f'{self.BASE_DIR}/dehydrated', '--register', '--accept-terms'])

    def get_certificate(self):
        if not os.path.isfile(self.CONFIG_FILE_PATH):
            try:
                print(f"{self.CONFIG_FILE_PATH} missing. Creating config file from given parameters.")
                self.generate_config()
            except:
                print("Could not create config file!")
                print(f"{self.CONFIG_FILE_PATH} missing. File not found!")
                exit(1)

        if not os.path.isfile(self.DOMAINS_FILE_PATH):
            try:
                print(f"{self.DOMAINS_FILE_PATH} missing. Creating domains file from given domains.")
                self.generate_domains_file()
            except:
                print(f"{self.DOMAINS_FILE_PATH} missing. File not found!")
                exit(1)
        
        self.register()
        self.execute()

    def execute(self):
        subprocess.run([f'{self.BASE_DIR}/dehydrated', '-c', '--config', self.CONFIG_FILE_PATH])

    def raw_execute(self):
        command = [ f'{self.BASE_DIR}/dehydrated' ]
        command.extend(self.RAW_EXEC_ARGS)
        subprocess.run(command)


class ALPNServer:
    @staticmethod
    def run_alpn_server():
        HOST, PORT = "0.0.0.0", 443
        server = ThreadedTCPServer((HOST, PORT), ThreadedTCPRequestHandler, bind_and_activate=False)
        server.allow_reuse_address = True
        print(f"ALPN Server bind on {HOST}:{PORT}")
        try:
            server.server_bind()
            server.server_activate()
            server.serve_forever()
        except Exception as e:
            print(e)
            server.shutdown()
            
            
            # subprocess.run(['python3', 'alpn-responder.py'], stdout=outfile)

def validate_domain_input(args):
    if not (args.domains_file or args.domains):
        print("""
              Domains or Domains file required.
              -d or --domains for comma-separated list of domains or --domains_file for file consisting domains.
              """)
        exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="""
                                     Wrapper for dehydrated.
                                     Entrypoint script for setting up Let's Encrypt certificates via TLS-ALPN-01.
                                     """)
    
    parser.add_argument("command",
                        nargs='?',
                        default="exception-shock-courier",
                         help="""
                        <NONE> | certonly | dehyrated-raw | alpn-server
                         """)
    
    parser.add_argument('-s','--staging',
                        action='store_true',
                        help="Use Let's Encrypt staging environment.")
    
    parser.add_argument('-d','--domains',
                        type=str,
                        required=False,
                        help="Comma-separated list of domains. Example: example.com,www.example.com,a.example.com,b.example.com")
    
    parser.add_argument('--domains_file',
                        type=str,
                        required=False,
                        help="File consisting domains to request certificate for. Ensure domains are separated by line break.")
    
    parser.add_argument('--config_file',
                        type=str,
                        required=False,
                        help="File consisting config to request certificate with dehydrated. \
                            TEMPLATE: https://github.com/dehydrated-io/dehydrated/blob/master/docs/examples/config")

    args, unknownargs = parser.parse_known_args()

    if args.command == "dehyrated-raw":
        print("Running raw dehydrated. No config made by wrapper.")
        handler = CertificateHandler(raw_args=unknownargs)
        handler.raw_execute()
        exit(0)

    if args.command == "alpn-server":
        print("Running ALPN Responder...")
        ALPNServer().run_alpn_server()
        exit(0)

    
    def default_certificate_handler(args):
        domains_list = []
        validate_domain_input(args)
        if not args.domains_file:
            domains_list = args.domains.split(',')
        
        handler = CertificateHandler(staging=args.staging, domains=domains_list, domains_file=args.domains_file, config_file=args.config_file)
        handler.get_certificate()

    if args.command == "exception-shock-courier" or args.command == "certonly":
        default_certificate_handler(args)

    # elif args.command == "add-to-nginx-config":
    #     print("Adding certificate to nginx config.")
    #     pass
        
    else:
        print(f"""
              ERROR:  
              Unknown command f{args.command}. Try --help or -h for help.
              """)