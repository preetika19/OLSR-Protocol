python controller.py "topology1.txt" &

python node.py 0 1 "message from 0" 50 &
python node.py 1 1 &
python node.py 2 2 &
python node.py 3 2 "message from 3" 50 &
python node.py 4 4 & 
python node.py 6 6 &
python node.py 7 7 &
python node.py 8 8 &
python node.py 9 2 "message from 9" 25 &
