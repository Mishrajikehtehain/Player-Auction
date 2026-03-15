To Use The IPL player aution terminal there are few things that are to be taken care of.
a.CSV file schema (name,base_price,rating,type,role).
b.Streamlit
c.Matplotlib
d.Pandas
e.Numpy

Step 1: First convert any xlx file to desired schema.

Step 2: Then open the target.py app and feed it with the csv we obtained. The target rating will be shown.

Step 3: Open app.py and upload the file again along with target. 

Step 4: Continuosly Feed it with the data.


Target.py (Engine):

Basically to win any auction (generally) one needs to keep their overall rating above the average of the top 150 players( 10*15 as 15 min players to be taken).
So it becomes essential for us to determine our fair value (rating) for players, the lowest and the highest rated player they can buy.
The target.py serves the main role in determining the average of top players. With some more tweaks we use std deviation of 0.5 to 0.75 from mean value(<0.4 below mean)in order to maintain the rating.

App.py:
Uses pandas and numpy to cater our needs based on constraints ie the players based on their role.
Uses steamlit to show real time data of all the competetors and real time analysis of the market including fair value , inflation , inflated fair price etc.
The data can be used further to make decisions in real time and perform well in any auction.

*Note: The author has taken help from tools like gemini and openai to create dashboard using streamlit while all the mathematical ideas are their own.
The author is also keen to take suggestions on missed topics and is willing to add them in future.
This program may contain some errors and may have missed some topics.
