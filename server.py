import socket
import os
import json
from subprocess import Popen, PIPE

# Initialize the server socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

#Constants
PORT_NUMBER=2728
RESOURCE_DIRECTORY="htdocs"
PHP_SUPPORTED_EXTENSTION_LIST=["php","html"]
SERVER_URL=f"http://localhost:{PORT_NUMBER}"



def main():
    # Bind the server socket to the specified port
    server_socket.bind(('', PORT_NUMBER))
    server_socket.listen(1)
    while True:
        # Accept incoming client connections
        connection, client_address = server_socket.accept()
        handle_client(connection,client_address)


def handle_client(connection,client_address):
    try:
        data = connection.recv(4096).decode("utf-8")
        print(data)
        if len(data):
            
            request_header_details_dict = get_request_header_details_dict( data ) # Get header details from recived data. 

            status_details_dict = get_status_details_dict( request_header_details_dict["resource_path"] ) # Geting the status details for response header
            
            resource=fetch_resource(**request_header_details_dict,**status_details_dict) # if the resource is available, get the byte version of it. Else it will return the 404.html
            
            response=create_new_response(request_header_details_dict["protocol"],status_details_dict,resource) #creating a new response: Basically this combines the response headers with resource data

            connection.send(response)
            connection.close()

    except Exception as error:
        print(f"{error}")
    
    print("Client disconnected...")


def get_request_header_details_dict(data):
    # Parse the request to extract method, resource path, protocol, and parameters
    request_line = data.split('\r\n')[0]
    method, resource_path, protocol = request_line.split()
    parameters={}

    if method=="GET":
        resource_path+="?"
        query_string=resource_path.split("?")[1]
        resource_path=resource_path.split("?")[0]
    else:
        query_string=data.splitlines()[-1]

    parameters=parse_parameters_from_path(query_string)
    
    resource_path=decide_resource_file_path(resource_path)
    resource_path=resource_path.replace("//","/")

    return {
        "method":method,
        "resource_path":resource_path[1:], # Remove the leading '/'
        "protocol":protocol,
        "parameters":parameters
    }

def decide_resource_file_path(resource_path):
    """
        Will make sure that the resource_path is in a default format
    """
    if not resource_path.count("."):
        if os.path.exists(f"{RESOURCE_DIRECTORY}/{resource_path}/index.php"):
            return resource_path+"/index.php"
        return resource_path+"/index.html"
    return resource_path
    

def parse_parameters_from_path(path):
    # Parse query string into a dictionary
    parameters={}
    if path.count("="):

        for single_query in path.split("&"):
            variable,value=single_query.split("=")
            parameters[variable]=value

    return parameters


def get_status_details_dict(resource_path):
    # Determine the status code and message based on resource availability
    status_details_dict={"status_code":0,"message":"NULL"}

    if os.path.exists(f"./{RESOURCE_DIRECTORY}/{resource_path}"):
        status_details_dict["status_code"]=200
        status_details_dict["message"]="OK"
    else:
        status_details_dict["status_code"]=404
        status_details_dict["message"]="Not Found"
    
    return status_details_dict

def fetch_resource(**kwargs):
    method=kwargs["method"]
    path=kwargs["resource_path"]
    parameters=kwargs["parameters"]

    if kwargs["status_code"]==404:
        with open(f"./{RESOURCE_DIRECTORY}/404.html","rb") as resource:
            return resource.read()


    if path.split(".")[-1] in PHP_SUPPORTED_EXTENSTION_LIST:
        #if the resource is a php or html file, we will treat it differently compared to other resources
        output=fetch_php_output(method,path,parameters)
        return output
    else:
        # if the resource isn't a php or html, it only needs to return the byte encoded data
        with open(f"./{RESOURCE_DIRECTORY}/{path}","rb") as resource:
            return resource.read()



def fetch_php_output(method,resource_path,parameters):
    
    payload=json.dumps({
        "method":method,
        "resource_path":resource_path,
        "parameters":parameters
    })
    # This payload contains the metadata from the client as a JSON string object.
    # It will be passed into the wrapper.php, which in turn executes the resource path.

    process = Popen(["./php/php",f"./{RESOURCE_DIRECTORY}/wrapper.php",payload], stdout=PIPE,cwd="./")
    # Pass the metadata to the wrapper.php as a command-line argument

    (output, error) = process.communicate()
    process.wait()
    print(output.decode("utf-8"))
    # Get and return the data from the subprocess. This is already encoded in byte format
    
    return output

def create_new_response(protocol,status_details_dict,resource):
    print(status_details_dict)
    response = f"{protocol} {status_details_dict['status_code']} {status_details_dict['message']}".encode("utf-8")+b'\r\n'
    response += b"Content-Type: text/html\r\n"
    response += b"\r\n"
    
    if status_details_dict["status_code"]==200:
        response+=resource
    else:
        response+=resource

    return response


if __name__=="__main__":
    print(f"Server running on {SERVER_URL}")
    main()


