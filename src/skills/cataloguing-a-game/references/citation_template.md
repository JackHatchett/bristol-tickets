# citation_template — a video game as a Zotero record

The field set every video-game collection uses, whatever the collection. A
point-and-click adventure and a strategy game differ in which collection they
land in and in their tags, and in nothing else here.

Zotero's item type is **Software**, stored as `computerProgram`. Its creator
types are `programmer` and `contributor`, and it has no others.

## The fields

| Zotero field | Payload key | Required | What goes in it |
| --- | --- | --- | --- |
| Title | `title` | Yes | The full title as the title screen gives it, subtitle and punctuation included. |
| Programmer | `developer` | Yes | The studio that made it, stored as a single-field name. This is the creator a citation renders as the author. |
| Contributor | `contributors` | No | A credited individual worth naming — the designer, the writer — as `Last, First`. Omit rather than list a whole credits roll. |
| Company | `publisher` | No | The publisher. Zotero maps this field to `publisher`, which is why the developer is not in it. |
| Date | `date` | Yes | `YYYY`, `YYYY-MM` or `YYYY-MM-DD`, of the release this record is about. A year alone is a complete answer. |
| System | `system` | Yes | The platform of that release: `DOS`, `Amiga`, `Macintosh`, `Windows`. One platform, not a list. |
| Version | `version` | No | What the release calls itself — a version string where it states one, else the release's own name: `Original release`, `CD-ROM re-release`. |
| Series Title | `series` | No | The franchise: `King's Quest`, `Monkey Island`. Blank for a standalone game. |
| Abstract | `abstract` | No | Two to four sentences of premise. See §The synopsis. |
| Place | `place` | No | Where the publisher published from in the year of release, `City, State`. Blank unless a source states it. |
| URL | `url` | Yes | The source page the record was built from. |
| Accessed | `accessed` | No | `YYYY-MM-DD`, the day that page was read. |
| Library Catalog | `catalog` | Yes | The database that supplied the identity: `The Adventure Game Database`, `MobyGames`. |
| Archive | `archive` | No | Where a playable copy is preserved: `Internet Archive`. |
| Loc. in Archive | `archive_location` | No | Its identifier inside that archive. |
| Short Title | `short_title` | No | An abbreviation worth having: `KQ5`. |
| Call Number | `call_number` | No | A shelf mark, where the user keeps physical copies. |
| Rights | `rights` | No | A stated licence. Availability — abandonware, on sale again — is not a licence and goes in `extra`. |
| Extra | `extra` | No | One `Key: value` per line. See §The extra keys. |
| Tags | `tags` | No | See §Tags. |

**Prog. Language is never used.** On a Software item Zotero's only language
field means the language the program was written in. A natural language is
`Language: en` in `extra`, which is the line Zotero reads as the citation
language.

## The extra keys

`extra` is Zotero's escape hatch and the library already uses it as one
`Key: value` per line. The keys a game record uses:

| Key | Holds |
| --- | --- |
| `Language` | The language played, as a code: `en`. |
| `Engine` | The interpreter or engine: `SCI1`, `SCUMM`, `AGI`. |
| `Also released for` | Every other platform, semicolon-separated, with years where they differ from the record's date. |
| `Adapted from` | The novel, film or game the work adapts, with its author and year. |
| `Availability` | How a copy can be had now: `Abandonware`, `Sold on GOG`, `Out of print`. |

Add a key only where the fact is bibliographic. A walkthrough, a review, a
design analysis or a full plot summary is a separate document and not a line
here.

## The synopsis

Two to four sentences. Who the player is, what situation the game opens in, and
what distinguishes the game itself — an interface first, an adaptation, a
technical first. It stops before the puzzles and the ending.

## Tags

Tags carry what the collection does not. Take the vocabulary from The Adventure
Game Database's own tags rather than inventing one, and keep to the ones that
would be used to find the game again: the control scheme, the perspective, the
setting or genre.

## A worked entry

```json
{
  "title": "King's Quest V: Absence Makes the Heart Go Yonder!",
  "short_title": "KQ5",
  "series": "King's Quest",
  "developer": "Sierra On-Line",
  "contributors": ["Williams, Roberta"],
  "publisher": "Sierra On-Line",
  "date": "1990-11-09",
  "system": "DOS",
  "version": "Original release",
  "place": "Oakhurst, California",
  "abstract": "The wizard Mordack steals King Graham's castle...",
  "url": "https://www.adventuregamedb.com/g/kings_quest_v_absence_makes_the_heart_go_yonder",
  "accessed": "2026-08-31",
  "catalog": "The Adventure Game Database",
  "archive": "Internet Archive",
  "archive_location": "msdos_Kings_Quest_V_-_Absence_Makes_the_Heart_Go_Yonder_1990",
  "extra": {
    "Language": "en",
    "Engine": "SCI1",
    "Also released for": "Amiga; Macintosh; FM Towns; NEC PC-9801; Windows 3.x; NES (1992)"
  },
  "tags": ["Point and click", "Third-person", "Fantasy"]
}
```
