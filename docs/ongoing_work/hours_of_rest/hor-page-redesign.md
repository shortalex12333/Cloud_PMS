  Plan: HoR Page Redesign                                                                             
                                                          
  What changes                                                                                        
                                                                                                      
  Current: /hours-of-rest → generic list page (DomainListView) → click row → detail lens
  New: /hours-of-rest → role-aware operational dashboard with inline input                            
                                                                                                      
  Crew View                               


the idea is crew cna drag the slider between when the start, to when they finsihed. either from selecting and draging slider. or when mousr clicks on to the line, it will generate new time slot from that point. 
for example, user clicks on 7am, two "+" appears at 7am. they drag this to 12pm. now they have "+" fomr 7am<->12pm. Next the crew memebr clciks 2pm, now a new two "+" appears, leaving the remainder in tact. 
for deleting recoreds BEFORE submitting, we need ot dcide how to do this cleanly and undersndbly. either button at the end of time frame that says "clear" or somethign else.

further more, crew can isnert their regualr horus via a temaplte they set. this requries a user input of "Create Time temaplte", giving it a name, schedule, days included (mon-sun), and therefore they can simply insert "insert my temaplte". which popualtes the week in question WITHOUT their signature. this means their signature is required at ALL times.

we need to have an alert section for whe users are NOT signing their hHOR (its a wekly requirement and notified in ledger_notification, linking to the page in question), this means we need ot highlgiht via red hue. 

                                          
                                                                                                      
  ┌─────────────────────────────────────────┐                                            
  │ My Time                                 │                                                        
  │                                         │                                           
  │ ┌─ THIS WEEK (Apr 7-13) ──────────────┐ │
  │ │ Mon  8h work / 16h rest       ✓     │ │                                                        
  | |  <---+++++++--+++++++---------->    | |
  | |                                     | | 
  │ │ Tue  10h work / 14h rest      ✓     │ │                                                        
  | |  <---+++++++--+++++++---------->    | |
  | |                                     | |     
  │ │ Wed  9h work / 15h rest       ✓     │ │                                                        
  | |  <---+++++++--+++++++---------->    | |
  | |                                     | |                                                          
  │ │ Thu  9h work / 15h rest       ✓     │ │                                                         
  | |  <---+++++++--+++++++---------->    | |
  | |                                     | |                                                         
  │ │ Fri  —                              │ │
  │ │ Sat  —                              │ │                                                         
  │ │ Sun  —                              │ │                                            
  │ │          [Submit Days For approval] │ │.
  │ └─────────────────────────────────────┘ │                                            
  │                                         │                                                        
  │ ┌─ COMPLIANCE ────────────────────────┐ │
  │ │ 24h rolling: ✓ 14h rest (min 10)    │ │                                                          
  │ │ 7-day rolling: ✓ 45h rest (min 77)  │ │                                             
  │ │ This week: 27h worked               │ │
  │ │ MLC status: COMPLIANT               │ │                                                          
  │ └─────────────────────────────────────┘ │    
  │                                         │                                                        
  │ ┌─ MONTHLY SIGN-OFF ─────────────────-┐ │                                             
  │ │ March 2026: Awaiting your sign      │ │                                                          
  │ │ [Review & Sign]                     │ │                                             
  │ └─────────────────────────────────────┘ │
  │                                         │   
  │ ┌─ HISTORY ────────────────────────-──┐ │              
  │ │ ▸ Week of Mar 31 - Apr 6            │ │                                                           
  │ │ ▸ Week of Mar 24 - Mar 30           │ │                                                           
  │ │ Analytics: avg 8.5h/day worked      │ │                                                          
  │ └─────────────────────────────────────┘ │                                                         
  └─────────────────────────────────────────┘                                            
   
### submit button therefore has pop up for signature required as per our requirements. i trust you udnerstnad this.  

=====

  ### HOD View                                                                                            
hod has two view, either "My time" or "Department View". department view is seen below:

  ┌─────────────────────────────────────────┐                                                         
  │ My Time    (Department View)            │                                                        
  │                                         │   
  │ ┌─ TODAY ─────────────────────────────┐ │                                                         
  │ │ 3/5 crew submitted                  │ │                                                          
  │ │ ⚠ Missing: John D., Mike T.         │ │                                                           
  │ └─────────────────────────────────────┘ │                                                         
  │                                         │                                                        
  │ ┌─ PENDING COUNTER-SIGNS ────────────-┐ │                                             
  │ │ March: 4 crew awaiting HOD sign     │ │                                                          
  │ │ [Review & Counter-Sign]             │ │                                                          
  │ └─────────────────────────────────────┘ │             
  │                                         │                                                        
  │ ┌─ CREW GRID (this week) ────────────-┐ │                                             
  │ │ Name     Mon  Tue  Wed  Thu  Fri    │ │     
  │ │ Jane S.  8h   9h   10h  8h   —      │ │               
  │ │ Mike T.  8h   —    —    —    —      │ │                                                           
  │ │ Chris L. 10h  10h  8h   9h   —      │ │
  │ └───────────────────────────────────-─┘ │                                                         
  │                                         │                                           
  │ ┌─ DEPT COMPLIANCE ─────────────────-─┐ │                                                          
  │ │ Violations this month: 0            │ │                                             
  │ │ All crew within MLC limits ✓        │ │                                                          
  │ └─────────────────────────────────────┘ │             
  └─────────────────────────────────────────┘                                                         

=====

  ### Captain/Fleet manager View                                                                                        
Each of the representive memebers of this bracket MUST BE ABLE TO USE MY TIME FEATURE TO SUBMIT THEIR OWN TIMES! otherwise they can also see "All departments"                                                       
  ┌─────────────────────────────────────────┐                                                         
  │ My time  (All Departments)              │                                                        
  │                                         │                                                        
  │ ┌─ VESSEL COMPLIANCE ───────────────-─┐ │                                             
  │ │ Engineering  5/5 compliant    ✓     │ │                                                          
  │ │ Deck         3/4 compliant    ⚠     │ │                                                          
  │ │ Interior     3/3 compliant    ✓     │ │
  │ └─────────────────────────────────────┘ │                                                         
  │                                         │                                           
  │ ┌─ PENDING FINAL SIGNS ─────────────-─┐ │                                                          
  │ │ March: 2 signoffs ready for Capt    │ │                                             
  │ │ [Review & Final-Sign]               │ │                                                          
  │ └─────────────────────────────────────┘ │                                            
  │                                         │   
  │ ┌─ ALL CREW (this week) ────────────-─┐ │              
  │ │ Full vessel grid by department      │ │     
  │ └─────────────────────────────────────┘ │                                                         
  │                                         │
  │ ┌─ ANALYTICS ───────────────────────-─┐ │                                                          
  │ │ Avg hours worked/crew/week: 42h     │ │                                             
  │ │ Compliance rate: 98%                │ │                                                          
  │ │ Violations this quarter: 1          │ │                                                          
  │ └─────────────────────────────────────┘ │             
  └─────────────────────────────────────────┘        