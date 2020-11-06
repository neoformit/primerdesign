#!/usr/bin/env bash

sudo apt install -y build-essential g++ cmake git-all

cd design
git clone https://github.com/primer3-org/primer3.git primer3
cd primer3/src
make

printf "\nRunning tests...\n"
result=`make test | grep -v "Testing completed" | grep -i failed`
if [[ result != '' ]]; then
    echo "Result:"
    echo "$result"
    printf "\nPrimer3 build tests failed\n"
    echo "Sorry, you're going to have to do the primer3 setup manually!"
    echo "Check out the github repo: https://github.com/primer3-org/primer3"
else
    echo "Primer3 install successful"
    echo "The app should now be functional. Test it by running:"
    echo "    $ python manage.py runserver --insecure"
fi
