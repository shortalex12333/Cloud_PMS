
### Issue 1 RECEIVING
- Currently the following pages have yet to be opstimsed. both in abckend and frontend logic and styling:
    - https://app.celeste7.ai/receiving

IF we use the branded /skill custom we have, as well as the branding local folder ( Location= /Documents/CelesteOS-Branding) we can see how the list view on each apge is false. it is legayc styling system.
the following tasks need to be conducted.
1. Find out where (tbale and filtration) we fetch column, tbales and data from tenant DB to reach page to laod frontend
2. Understand and list of these values, and create a lsit of:
    - of the vales: 1) which vlaues are Human-readable? vs. 2) which are backend hidden?. forexample "UUID" are not necassary to showcase frontend, this woudl class as "backend hidden" defined.
3. Ensure that of these values fetch, we adhere to the RLS, RBAC and security lgoic as seen in other pages. For example "FETCH WHERE YACHT_ID= *<users signed in yacht_id>* AND fleet_id=*<users signed in fleet_id>* "
**CURRENT CONSOLE ERRORS** : - Current 404 issue with "receiving" when user opens any card = 2724-85fa7beac9eeab29.js?dpl=dpl_A4GPF7PhBzM6ayf8yejSZFpseTqF:24  GET https://qvzmkaamzaqxpzbewjxe.supabase.co/rest/v1/pms_receiving?select=id%2Cvendor_name%2Cvendor_reference%2Cstatus%2Creceived_date%2Cnotes%2Cpo_number%2Ccreated_at&id=eq.ac137d1e-2aa1-4eb6-b225-231d5d85f923 404 (Not Found)
(anonymous) @ 2724-85fa7beac9eeab29.js?dpl=dpl_A4GPF7PhBzM6ayf8yejSZFpseTqF:24
(anonymous) @ 2724-85fa7beac9eeab29.js?dpl=dpl_A4GPF7PhBzM6ayf8yejSZFpseTqF:24
await in (anonymous)
then @ 2724-85fa7beac9eeab29.js?dpl=dpl_A4GPF7PhBzM6ayf8yejSZFpseTqF:1
postMessage
l @ 2117-a09c10e2f0bd6d8e.js?dpl=dpl_A4GPF7PhBzM6ayf8yejSZFpseTqF:1
M @ 2117-a09c10e2f0bd6d8e.js?dpl=dpl_A4GPF7PhBzM6ayf8yejSZFpseTqF:1
postMessage
l @ 2117-a09c10e2f0bd6d8e.js?dpl=dpl_A4GPF7PhBzM6ayf8yejSZFpseTqF:1
x @ 2117-a09c10e2f0bd6d8e.js?dpl=dpl_A4GPF7PhBzM6ayf8yejSZFpseTqF:1
t.unstable_scheduleCallback @ 2117-a09c10e2f0bd6d8e.js?dpl=dpl_A4GPF7PhBzM6ayf8yejSZFpseTqF:1
nS @ fd9d1056-55335c623957b5aa.js?dpl=dpl_A4GPF7PhBzM6ayf8yejSZFpseTqF:1
nw @ fd9d1056-55335c623957b5aa.js?dpl=dpl_A4GPF7PhBzM6ayf8yejSZFpseTqF:1
(anonymous) @ fd9d1056-55335c623957b5aa.js?dpl=dpl_A4GPF7PhBzM6ayf8yejSZFpseTqF:1
2724-85fa7beac9eeab29.js?dpl=dpl_A4GPF7PhBzM6ayf8yejSZFpseTqF:24  GET https://qvzmkaamzaqxpzbewjxe.supabase.co/rest/v1/pms_receiving?select=id%2Cvendor_name%2Cvendor_reference%2Cstatus%2Creceived_date%2Cnotes%2Cpo_number%2Ccreated_at&id=eq.ac137d1e-2aa1-4eb6-b225-231d5d85f923 404 (Not Found)
(anonymous) @ 2724-85fa7beac9eeab29.js?dpl=dpl_A4GPF7PhBzM6ayf8yejSZFpseTqF:24
(anonymous) @ 2724-85fa7beac9eeab29.js?dpl=dpl_A4GPF7PhBzM6ayf8yejSZFpseTqF:24
await in (anonymous)
then @ 2724-85fa7beac9eeab29.js?dpl=dpl_A4GPF7PhBzM6ayf8yejSZFpseTqF:1
setTimeout
setTimeout @ 1632-824ca3eb12739289.js?dpl=dpl_A4GPF7PhBzM6ayf8yejSZFpseTqF:1
setTimeout @ 1632-824ca3eb12739289.js?dpl=dpl_A4GPF7PhBzM6ayf8yejSZFpseTqF:1
(anonymous) @ 1632-824ca3eb12739289.js?dpl=dpl_A4GPF7PhBzM6ayf8yejSZFpseTqF:1
O @ 1632-824ca3eb12739289.js?dpl=dpl_A4GPF7PhBzM6ayf8yejSZFpseTqF:1
(anonymous) @ 1632-824ca3eb12739289.js?dpl=dpl_A4GPF7PhBzM6ayf8yejSZFpseTqF:1
Promise.catch
m @ 1632-824ca3eb12739289.js?dpl=dpl_A4GPF7PhBzM6ayf8yejSZFpseTqF:1
start @ 1632-824ca3eb12739289.js?dpl=dpl_A4GPF7PhBzM6ayf8yejSZFpseTqF:1
fetch @ 1632-824ca3eb12739289.js?dpl=dpl_A4GPF7PhBzM6ayf8yejSZFpseTqF:1
#Q @ 1632-824ca3eb12739289.js?dpl=dpl_A4GPF7PhBzM6ayf8yejSZFpseTqF:1
onSubscribe @ 1632-824ca3eb12739289.js?dpl=dpl_A4GPF7PhBzM6ayf8yejSZFpseTqF:1
subscribe @ 1632-824ca3eb12739289.js?dpl=dpl_A4GPF7PhBzM6ayf8yejSZFpseTqF:1
(anonymous) @ 1632-824ca3eb12739289.js?dpl=dpl_A4GPF7PhBzM6ayf8yejSZFpseTqF:1
rQ @ fd9d1056-55335c623957b5aa.js?dpl=dpl_A4GPF7PhBzM6ayf8yejSZFpseTqF:1
...
...
...
o @ fd9d1056-55335c623957b5aa.js?dpl=dpl_A4GPF7PhBzM6ayf8yejSZFpseTqF:1
M @ 2117-a09c10e2f0bd6d8e.js?dpl=dpl_A4GPF7PhBzM6ayf8yejSZFpseTqF:1
postMessage
l @ 2117-a09c10e2f0bd6d8e.js?dpl=dpl_A4GPF7PhBzM6ayf8yejSZFpseTqF:1
M @ 2117-a09c10e2f0bd6d8e.js?dpl=dpl_A4GPF7PhBzM6ayf8yejSZFpseTqF:1
postMessage
l @ 2117-a09c10e2f0bd6d8e.js?dpl=dpl_A4GPF7PhBzM6ayf8yejSZFpseTqF:1
x @ 2117-a09c10e2f0bd6d8e.js?dpl=dpl_A4GPF7PhBzM6ayf8yejSZFpseTqF:1
t.unstable_scheduleCallback @ 2117-a09c10e2f0bd6d8e.js?dpl=dpl_A4GPF7PhBzM6ayf8yejSZFpseTqF:1
nS @ fd9d1056-55335c623957b5aa.js?dpl=dpl_A4GPF7PhBzM6ayf8yejSZFpseTqF:1
nw @ fd9d1056-55335c623957b5aa.js?dpl=dpl_A4GPF7PhBzM6ayf8yejSZFpseTqF:1
(anonymous) @ fd9d1056-55335c623957b5aa.js?dpl=dpl_A4GPF7PhBzM6ayf8yejSZFpseTqF:1

4. list all action buttons listed as per each lens and whetehr this is legibile and purposeful to have. as well as the role security with each. here is my draft, in the format of " BUTTON | KEEP/REMOVE \ ROLE SECURITY | NOTES



-----



### Issues 2. - receiving
- current beahour, we ar ereciving 404 errors when signed in as cpatian for the following button on the purchase order drop down, ALL button have 400 erros;
currently with "recieving" the code is fetching items from the wrong db, it is wired to fetch master (which is false) and should be wire to fetch from TENANT db. Tenant env vars are in rende,r abckend deployment. an vercel (frontend hosting) has env vars for the master db. probably where mistakes lies within. this fault leads to a 404 console error.


### Issues 3 - REceiving UUID
- not only is the content not viisble t epxand and see the cards on receiving, but also UUID are visible for the user, this is compeltely WRONG! we never share UUID, we need to define of the meattdat avaible through receiving lens, what is illustrated on the frontend to the user (title, descr perosn, time) and what is hidden backend (uuid, id's etc.).
- list all features possible, what is seen in other areas of the site, such as shopping, inventory, how they articualte adn how we can better provide this insight.


### Issues 4
- right now the filtering across all lens's is weak. we need to conduc the following task.
1. list each tbale which we derrive valaues form tennant db. and categorise with what is leible for frontend rendering for users to see, and what needs to be hidden, such ass UUID.
then ensure we are illustrating all relevant information accoridnglynot duplcaites vlaues as both entries for different KEY names, and ensure clear.
for mvp just ensure we get the information rpesent, dont worry too much about frontend ux styling, just match that what exists, ALWAYS USE TOKENISED SYSTEMS

### Issues 5 -  receiving 
- these lsns's were created, biut never optimsied. each button rendered in the same position fo rthe correposdning lens's "long receipt", all action nohting. they do nothign, no popup, no errors, never wired to any degree.
currently with "shopping list" the code is fetching items from the wrong db, it is wired to fetch master (which is false) and should be wire to fetch from TENANT db. Tenant env vars are in rende,r abckend deployment. an vercel (frontend hosting) has env vars for the master db. probably where mistakes lies within. this fault leads to a 404 console error.
