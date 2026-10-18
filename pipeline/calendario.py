"""Calendario editoriale settimanale: a ogni giorno corrisponde un angolo di contenuto.

Gli angoli vengono dalla ricerca sui temi più richiesti nella nicchia tech italiana (ottobre 2026).
I giorni senza angolo restano liberi: li coprono le bozze nate dai post di @technologybrief
(notizie spiegate, siti e app utili) o i post scritti a mano.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Angolo:
    nome: str
    pubblico: str
    leva: str
    istruzioni: str
    esempi: tuple[str, ...]


AI_QUOTIDIANA = Angolo(
    nome="L'AI nella vita di tutti i giorni",
    pubblico="Curiosi di tecnologia tra 20 e 45 anni che hanno provato un chatbot una volta e poi hanno smesso.",
    leva="Desiderio (risparmiare tempo) e dolore (sentirsi indietro).",
    istruzioni=(
        "Scegli UN compito concreto e frequente (casa, lavoro, studio, burocrazia) e mostra come farlo con un "
        "chatbot gratuito. Ogni slide pratica contiene il prompt esatto da copiare, tra virgolette, e cosa "
        "aspettarsi come risposta. Ricorda di non incollare dati personali sensibili. Niente nomi di piani a "
        "pagamento o prezzi se non sei certo che siano attuali."
    ),
    esempi=(
        "5 cose noiose della settimana da far fare a un chatbot gratis (prompt inclusi)",
        "Leggere una bolletta o un contratto con l'AI senza dare via i tuoi dati",
        "Perché l'AI ti risponde male: 4 errori nei prompt e come correggerli",
    ),
)

TRUFFE = Angolo(
    nome="Il kit anti-truffa da girare in famiglia",
    pubblico="Chi in famiglia è 'quello che se ne intende' e riceve gli screenshot dei genitori.",
    leva="Dolore (soldi persi, familiari esposti) e identità (proteggere i propri cari).",
    istruzioni=(
        "Scegli UN tipo di truffa diffuso in Italia (SMS di finti pacchi o rimborsi, finta banca al telefono, "
        "voce clonata, marketplace, finti lavori) e spiega come riconoscerla in pochi secondi: i segnali, "
        "cosa NON fare, cosa fare se si è già cliccato. Gli esempi di messaggi sono ricostruiti e generici: "
        "mai numeri di telefono o link reali. Nell'ultima slide invita a inviare il post a chi ne ha bisogno."
    ),
    esempi=(
        "6 SMS truffa arrivati agli italiani nel 2026: trova l'errore in 5 secondi",
        "La parola d'ordine di famiglia contro le chiamate con voce clonata",
        "Pacco in giacenza da 2,99 €: cosa succede davvero se clicchi",
    ),
)

DURATA_DISPOSITIVI = Angolo(
    nome="Non cambiare dispositivo, sistemalo",
    pubblico="Chi ha un portatile di 5-8 anni o un telefono lento e sta pensando di cambiarlo mentre i prezzi salgono.",
    leva="Dolore (rincari, fine del supporto) e desiderio (sentirsi furbi).",
    istruzioni=(
        "Scegli UN problema concreto (PC lento, memoria del telefono piena, batteria che dura poco, PC che non "
        "supporta Windows 11) e dai passaggi verificabili, dal più facile al più impegnativo, con costo e tempo "
        "indicativi per ognuno (es. '0 €, 10 minuti'). Smonta anche i falsi miti. Niente consigli rischiosi "
        "per i dati senza ricordare il backup."
    ),
    esempi=(
        "Prima di comprare un PC nuovo: 5 controlli che ti fanno risparmiare centinaia di euro",
        "Telefono lento? I 4 passaggi che funzionano davvero (e i 3 miti da ignorare)",
        "Il PC non supporta Windows 11: le tue 3 strade, dalla più facile alla più economica",
    ),
)

MENO_ABBONAMENTI = Angolo(
    nome="Un abbonamento in meno al mese",
    pubblico="Appassionati di tecnologia che pagano troppi servizi digitali e vogliono tagliare senza perdere comodità.",
    leva="Dolore (spesa che cresce) e identità (controllo dei propri dati).",
    istruzioni=(
        "Scegli UN servizio a pagamento molto diffuso (archiviazione foto, cloud, musica, password manager, "
        "office, VPN) e proponi alternative gratuite, una tantum o da ospitare in casa (anche con un Raspberry Pi), "
        "una per slide, con difficoltà da 1 a 3 e cosa si perde rispetto all'originale. Prezzi solo come ordine "
        "di grandezza, e ogni prezzo va in `da_verificare`."
    ),
    esempi=(
        "Google Foto pieno? 4 alternative per le tue foto, dalla gratuita a quella in casa",
        "7 abbonamenti tech che puoi sostituire con qualcosa di gratis",
        "Un Raspberry Pi al posto di 3 abbonamenti: cosa serve davvero",
    ),
)

# 0 = lunedì ... 6 = domenica. None = giorno libero (bozze da @technologybrief o scritte a mano).
CALENDARIO: dict[int, Angolo | None] = {
    0: AI_QUOTIDIANA,
    1: TRUFFE,
    2: DURATA_DISPOSITIVI,
    3: AI_QUOTIDIANA,
    4: None,  # notizia tech spiegata
    5: MENO_ABBONAMENTI,
    6: None,  # siti e app utili
}
