GolfBot

Regler:
  - 11 bolde i alt (1 orange VIP-bold, 10 hvide)
  - Orange bold giver 200 bonuspoint HVIS den afleveres først
    (Vores robot holder boldene efter LIFO princippet)
  - Maal A (lille, 80mm): 150 point/bold
  - Maal B (stort, 200mm): 100 point/bold
  - 8 minutter til indsamling
  - -50 point per beroering af bane/forhindring

Strategi:

Vi vil detektere banen og alle objekter med et kamera. 
Vi har markeret hjørnerne af banen, de to mål og robotten med et Aruco mærkat.
Når programmet starter skal alle bolde og forhindringer detekteres, og der skal planlægges en rute for robotten, som går udenom alle forhindringer og som sørger for at robotten ikke kører ind i banderne.
Tiden starter først når robotten bevæger sig, så ruteplanlægning behøver ikke være hurtig, men skal være præcis.
Når robotten kører skal kameraet hele tiden sende inputs til robotten om hvilken kommando den skal køre for at forsætte mod sit mål koordinat.
drive_to_ball skal altid placere robotten lige ud for bolden med en vinkel som sikrer sig, at robotten ikke kører ind i en forhindring eller banden når ball_collection kører (robotten skal køre lidt frem mod bolden).
Når queue er tom for bolde, så skal robotten køre mod mål, og placere robotten foran mål og køre deliver ball.

Alle phaser skal laves i sit eget flow, så vi kan fejlsøge på de enkelte faser.
