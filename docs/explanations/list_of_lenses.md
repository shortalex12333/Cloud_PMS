lsit of lens's:
1. Documents (where we store manuals, ingest docuemnts from the background worker on aychts native pc, read only of NAS and upload to the celeste "cloud" AKA supabase storage, adn index/ingest)
2. Certificates (this si CREW certifiicates such as STCW etc. as well as mny other certifiicates user uplaod, solas, and machinary etc. this MAY be under "document" due to ai contraints)
3. inventory (all ivnenory onbaord, this is popualted through exporting sql and uploading to celeste cloud, formatting. most suers will have idea_yacht software, ehnce we requested export and uplaod accordingly)
4. parts (simialr to inventroy, same journey concept)
5. Handover (as users ocntinue to work, they can simply add "add ot my hadnover", and popualte with scrap notes, our sste will already use formschema and vlookup frmo lens data in question and the orignial entity termtypes and vlaues to autp populate. this provides user will scrap notes of the hadnover. once their time on baord is finihed, such as every 2 motnhs, we use agentic workflwo to transcribe into professional manner. everythign is doucmented, hyperlinks to crrespding work to exact work roders etc. and user sign in/off fomr this.)
6. Hours of rest (no import fo rthis, start a fresh adn give crew tempaltes to use, which is industry standard. )
7. Work orders (is what it is. we import frm eisting software)
8. Faults (one way system, any crew submits faults found, respective engineers and crew undertake and link to work order. simple)
9. Receiving  (when suers recee parcel/shipment, they simply take picture of reciving and/or search for order/shopping lsit. detials the quanitties. this system auto creates the labels required if any discrepancies, we flag and auto write suppleir email for them. given the vlaues fomr the orignal shopping lsit. we NEVER send the emial, just write and prepare, its up to them to send.)
10. Shopping (users create draft orders, submit and send. tracking the udpates nad flow)
11. Email  (we wtahc eusers emaisl through microsoft grpah api, and auto link thes eincomng emais with SOC-2 compliant to link to existing work. for exmaple user ereives email about part update, or order update, we auotmatiaclly link to the shopping lsit i question, hence makigniit easier. stoping the bac and forth between apps and loss of data and continuity is maintained)
13. Equipment (system lsit, linsk to related lens data adjacet, simple stuf, imported fomr sql from origin software)


Hierarchy lsit of improtance:
Top tier
- Handover- auto creation
- Docuemnts- searhc for anythign to exact page via NLP

Medium
- Receiving 
- certificates (this hasnt really be done before. suers jsut store on lcaol pc and pray they dont forget where they are)
- email (could be good, in beta testing, hoenstly might eb more of a feature than asset)

Low
- inventory
- parts
- equipment
- faults
- work order
- hours of rest
- shopping list


=======

More features not mentioned that could be highley sueful
- SHOW_RELATED = we use the simialr pieplien tehcnology fo searching on main spotlight bar for show_related. this is where users are within a len of data, and can view ismilar adjacne tlenses containging aliek matches. for exmaple, work order bout amain engine will have "show_related" to sowcase handovers, notes, certifiicates, nv, parts etc. relating accoridngly.
- LEDGER = this si the adutiable log of everyhting any one does ever. anythign from read, write, open, clsoe, delete, create, acrhive, sign, move, assign etc. is all logged here. HOD can see whole department. gives credibiltiy during precise matters of importance to see if the work was gneuinly done, timestampz, opened sops etc. 