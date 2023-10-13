import socket
import threading

# Sends commands to server and prints info etc
def send_command(sock, cmd):
    print(f"Sending from {threading.current_thread().name}: {cmd}")
    sock.sendall((cmd + "\r\n").encode('utf-8'))

def irc_client(nickname):
    # Create an IPv6 TCP socket
    client_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    
    # Connect to the localhost on the 6667 port
    client_socket.connect(('::1', 6667))

    # Send NICK and USER commands to server
    send_command(client_socket, f"NICK {nickname}")
    send_command(client_socket, f"USER {nickname} 0 * :{nickname} user")

    # Naming thread after nickname
    threading.current_thread().name = nickname

    # Keep the client alive to receive data
    while True:
        data = client_socket.recv(1024)
        if not data:
            break
	
        print(f"Received for {nickname}:\n{data.decode('utf-8')}")

        # If t
        if f":server 001 {nickname}" in data.decode('utf-8'):
            input(f"Press Enter to send QUIT command for {nickname}...")
            send_command(client_socket, "QUIT :Leaving the server")

    client_socket.close()

if __name__ == "__main__":
    # Start multiple clients in threads
    # This will start 5 clients
    for i in range(5):  
        threading.Thread(target=irc_client, args=(f"client{i}",)).start()
