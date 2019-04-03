# Proxy-Server 
Eesha Dutta , Paryul Jain  

### OVERVIEW 
A Simple HTTP proxy server.  

### FEATURES 
1. Multi Threaded​ : can handle multiple clients and server 
2. GET and POST requests supported. 
3. Blacklisting of Domains : ​ some url’s blocked 
4. Caching : ​ fast servicing of requests. 
5. Authentication : ​ username and password required to view blacklisted domains 

### HOW TO RUN 
##### Proxy 
Run proxy server in proxy_server folder. Specify proxy port. 
`python proxy.py 20000`   
It will run proxy on port 20000 
 
##### Server 
Run server in server directory. Specify server port.   
`python server.py 19999` to run server on port 19999  
 
##### Client 
curl request can be sent as client request and get the response.   
`curl --request GET --proxy 127.0.0.1:20000 --local-port 20001-20010 127.0.0.1:19999/1.txt`   
This request will ask 1.txt file from server 127.0.0.1/19999 by GET request via proxy 127.0.0.1/20000 using one of the ports in range 20001-20010 on localhost. 

Valid username and password should be provided to access blacklisted servers.   
`curl --request GET -u username:password --proxy 127.0.0.1:20000 --local-port 20001-20010 
127.0.0.1:19998/1.data` 