"""
Protokol-ordbogen.
Disse funktioner bruges af både PC og EV3 til at oversætte 
mellem programmets kode og den tekst, der sendes over WiFi.

Det aftalte format er altid:
"KOMMANDO VÆRDI\\n" eller bare "KOMMANDO\\n"
"""

def create_command(command, value=None):
    """
    PC'en bruger denne til at lave en besked, inden den sendes.
    F.eks. create_command("FORWARD", 30) -> "FORWARD 30\\n"
    F.eks. create_command("STOP")        -> "STOP\\n"
    """
    if value is not None:
        return f"{command} {value}\n"
    return f"{command}\n"

def parse_command(message):
    """
    EV3'en bruger denne til at forstå, hvad den lige har modtaget.
    F.eks. modtager "TURN_TO -45\\n" 
           -> returværdi: ("TURN_TO", -45.0)
    """
    # 1. Fjern eventuelle linjeskift indsat for netværkets skyld
    message = message.strip()
    
    if not message:
        return None, None

    # 2. Split teksten op ved hvert mellemrum
    parts = message.split(' ')
    
    # 3. Den første del er altid vores kommando (f.eks. "FORWARD")
    command = parts[0]
    
    # 4. Hvis der står et tal efterfølgende (f.eks. "20"), læser vi det.
    if len(parts) > 1:
        try:
            value = float(parts[1])
        except ValueError:
            print(f"Fejl! Kunne ikke forstå {parts[1]} som et tal.")
            value = None
    else:
        value = None
        
    return command, value
