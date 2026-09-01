# Kalendarz v1.0a
Mój bot do zarządzania wydarzeniami
![cakendar_icon.png](icons/calendar_icon.png)

## Instalacja
- `git clone https://github.com/wiKapo/Kalendarz_DiscordBot`
- `cd Kalendarz_DiscordBot`
- `python3 -m venv ./.venv`
- `source .venv/bin/activate`
- `pip install -r requirements.txt`
- `python3 app.py`

## Wymagania
- python3.12
- sqlite3
- Plik `.env` w folderze `Kalendarz_DiscordBot`, który zawiera pola `BOT_TOKEN=<bot_token>` i `USERS=<user_id1,user_id2,...>`
Użytkownicy wpisani w polu `USERS` mają dostęp do wszystkich komend bota, w tym `/admin`.

## Komendy dostępne w bocie
> [!TIP]
> Wszystkie komendy dostępne dla użytkowników znajdują się również pod komendą `/help`

### 1. Polecenia kalendarza
- `/calendar create <title>` - Tworzy nowy kalendarz.
Można opcjonalnie podać nazwę kalendarza.
Kalendarz jest aktualizowany automatycznie, **codziennie o godzinie 0:00 UTC**.
W przypadku usunięcia **wiadomości** z kalendarzem wykonaj ponownie `/calendar create`, która odtworzy wiadomość kalendarza.
- `/calendar edit` - Otwiera okienko edycji kalendarza. Umożliwia zmianę tytułu oraz wybranie roli, która będzie wysyłać powiadomienia przy aktualizacji kalendarza.
- `/calendar delete` - Usuwa kalendarz z tego kanału **RAZEM z wydarzeniami**, które są przypisane tylko do tego kalendarza. Tej operacji nie można cofnąć.
- `/calendar update <calendar_id> <quiet>` - Aktualizuje kalendarz. Domyślnie wybierany jest kalendarz z kanału, na którym wykonano komendę.
Można podać id kalendarza, który ma być zaktualizowany. Można opcjonalnie ustawić `quiet` na `False`, aby powiadomić o aktualizacji.

### 2.  Polecenia niestandardowych sekcji
- `/section add <calendar_id>` - Dodaje sekcję do wybranego kalendarza. Można opcjonalnie podać id kalendarza do którego ma być dodana.
- `/section edit <calendar_id>` - Edytuje wybraną sekcję. Można opcjonalnie podać id kalendarza, z którego będzie edytowana sekcja.
- `/section delete <calendar_id>` - Usuwa wybrane sekcje. Można opcjonalnie podać id kalendarza, z którego będą usuwane sekcje.
  
### 3.  Polecenia wydarzeń
- `/event add` - Dodaje wydarzenie. Dodane wydarzenia będą usuwane po 3 tygodniach od dnia wydarzenia.
- `/event edit <calendar_id>` - Wysyła wiadomość z polem wyboru wydarzenia do edycji. Po wyborze wydarzenia otwiera okienko edycji.
Można podać id kalendarza, z którego będzie wybierane wydarzenie do edycji.
- `/event delete <calendar_id>` - Otwiera okienko z polem wyboru wydarzeń do usunięcia. Po wyborze wydarzeń usuwa je całkowicie. **Tej operacji nie można cofnąć**.
Można podać id kalendarza, z którego będą pobierane wydarzenia do usunięcia.
    

### 4.  Polecenia menedżerów
> [!TIP]
> Jeżeli chcesz aby inne osoby po za administratorami miały dostęp do bota, dodaj odpowiednie role poniższą komendą.  

Role menedżerów są dodawane przez administratorów na danym serwerze.
Menedżerowie otrzymują dostęp do wszystkich komend `/event` i `/section` na danym serwerze. Mogą również skorzystać z `/calendar edit` i `/calendar update`.  
**Menedżerowie nie mogą dodawać nowych menedżerów.**

- `/user set` - Otwiera okienko z polem wyboru ról dla menedżerów kalendarza.
    
### 5.  Inne polecenia
- `/about` - Pokazuje informacja o autorze
- `/help` - Pokazuje wiadomość opisującą dostępne polecenia dla użytkowników (czyli wszystkie powyższe)

### 6. Polecenia dla administratorów bota
> [!IMPORTANT]
> Aby skorzystać z poniższych komend bota, id użytkownika musi być dodane do listy `USERS` w pliku `.env`.

- `/admin update_all_calendars` - Aktualizuje wszystkie kalendarze przypisane do tego bota.
- `/admin create_test_calendar` - Tworzy testowy kalendarz.
- `/admin remove_admin_cog` - Usuwa tą grupę poleceń z bota.
- `/admin stop` - Zatrzymuje bota.

- `/admin update_db` - Do migrowania bazy danych z wersji starszych od v1.0.
- `/admin update_event_loggers` - Do wpisania informacji o lokalizacji wydarzeń.

## Loggery
- Każdy kalendarz ma swój własny logger, który jest zapisywany w pliku `calendar_<id>.log` w `/logs/calendar`.  
Zapisuje on wszystkie zmiany wprowadzone do kalendarza.
- Każde wydarzenie ma swój logger. Logger jest zapisywany w pliku `event_<id>.log` w `/logs/event`.  
Zapisuje on wszystkie zmiany wprowadzone do wydarzenia.
- Interakcje użytkownika z kalendarzem, zapisywane są w pliku `user_<nick>.log` w `/logs/user`.  
Przechowuje interakcje z systemem powiadomień
- **W razie błędu logi kierowane są również do pliku `error.log`.**
- Informacje o stanie bota są zapisywane w pliku `default.log`.
- Informacje o pętli powiadomień są zapisywane w pliku `notification.log`.

Wersja 1.0a