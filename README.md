# ItemCatalog
This application provides a list of items within a variety of categories and provides a user registration and authentication system using a google account. Registered users will have the ability to post, edit and delete their own items.

##Tecnologies
This project utilizes python, flask, sql alchemy, css and javascript, to create an Item catalog website.

##How to run
This simple web application uses google account for authentication and autorization. This means that it is necessary to have a valid google account and set up a client id and secret. When you obtain a client_secrets.json file, just put it in the same directory as the rest of the project. For more information go to http://console.developers.google.com

To spin this website up:

1. Download or clone the repository.
2. Initialize the Vagrant vm via vagrant up, which should set up on localhost:5000.
3. Connect to the virtual machine: vagrant ssh.
4. Navigate to the catalog directory: cd /vagrant/catalog
5. Start the server: python application.py
6. Navigate to it in your browser of choice at localhost:5000
