
### Issues 1 - Purchase order buttons
- current beahour, we ar ereciving 404 errors when signed in as cpatian for the following button on the purchase order drop down, ALL button have 400 erros;
Add PO Note
Create Purchase Request
Order Part
Approve Purchase
Add Item to Purchase
Update Purchase Status
Upload Invoice
Add to Handover

furhter buttons have differnet faults;
Delete Purchase Order - users can enter any random pin, and proceed with 0 failures, howveer the purchase order is NOT deleted. 
Track Delivery - refreshes apge, no console error, nothing happens.

Cancel Purchase Order - users can enter any random pin, and proceed with 0 failures, this is the only button that actually works.

below is list of buttons and comment snad action requiredby you. this is th in the format of: *button name* | keep/remove | rls| notes
# List of changes:
Add PO Note | KEEP | Purser, HOD of that department or captina allowed | 
Create Purchase Request | remove | na | this is wasteful, delete button and all wiring, this is only useful on the pge, not within a card
Order Part | KEEP | Purser, HOD of that department or captina allowed | 
Approve Purchase | KEEP | Purser, HOD of that department or captina allowed | 
Add Item to Purchase | KEEP | Purser, HOD of that department or captina allowed | this is only allowed IF status does not equal "sent/paid/complete" etc. must onyl be applicable during draft
Update Purchase Status | KEEP | Purser, HOD of that department or captina allowed | 
Upload Invoice | KEEP | Purser, HOD of that department or captina allowed | 
Add to Handover  This is one or our CORE feature. hence we need to ensure this is great. use th form schema to bring forward existing known vlaues of the data card in question. hence we already know specific id of the data in question title, status, then add optional inputs for users to isnert following key/values text input and "notes". the reaosn of using form-schema is to reduce fatigue from repeating insert for users nad maintaining great data inputs. get creative and allow drop down or any text insert allowed to key/value. the purpose os ifnormation collection and storage clearly.
Delete Purchase Order | KEEP | Purser, HOD of that department or captina allowed | 
Track Delivery | remove | na | this is wasteful, delete button and all wiring
Cancel Purchase Order | KEEP | Purser, HOD of that department or captina allowed | 

effectively the shopping lsit can be made by anyone onboard, but approval for payment adn logging is onl applicable for those ranks which are allowed to ahdnle partial finance-operations, hence why HOD only for their department, purser and captain for all purchase. 

======
### Issues 2 - Purchase orders metadata
- list all features possible, what is seen in other areas of the site, such as shopping, inventory, how they articualte adn how we can better provide this insight.
- we currently display terrible repeated weak metadata of the following:
title - title (yes this is genuiny fuckign repeated)
status (even though the stsu is alreayd viisble on the same row.)

- in contrast you are to plan what is avaible and what is desirebale, for exmaple, department, perosn submitted, no. of items, title, description brief, request data, etc.




### Issues 3
- right now the filtering across all lens's is weak. we need to conduc the following task.
1. list each tbale which we derrive valaues form tennant db. and categorise with what is leible for frontend rendering for users to see, and what needs to be hidden, such ass UUID.
then ensure we are illustrating all relevant information accoridnglynot duplcaites vlaues as both entries for different KEY names, and ensure clear.
for mvp just ensure we get the information rpesent, dont worry too much about frontend ux styling, just match that what exists, ALWAYS USE TOKENISED SYSTEMS

### Issues 4 -  purchase order
- these lsns's were created, biut never optimsied. each button rendered in the same position fo rthe correposdning lens's "Create PO", all action nohting. they do nothign, no popup, no errors, never wired to any degree.
currently with "shopping list" the code is fetching items from the wrong db, it is wired to fetch master (which is false) and should be wire to fetch from TENANT db. Tenant env vars are in rende,r abckend deployment. an vercel (frontend hosting) has env vars for the master db. probably where mistakes lies within. this fault leads to a 404 console error.
