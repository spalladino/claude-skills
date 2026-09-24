---
name: writing-well
description: Write and rewrite prose the way William Zinsser's "On Writing Well" teaches — simple, active, clutter-free, one thought per sentence, in one human voice. Use when the user invokes /writing-well, asks for a Zinsser-style pass, or wants any prose (chat replies, explanations, PR descriptions, docs, commit messages) tightened. Apply it to every sentence you write for the rest of the turn, then run the rewrite pass before sending.
---

# writing-well

Distilled from Zinsser, *On Writing Well* (6th ed.), keeping only what applies to an assistant
writing technical and explanatory prose. Fuller chapter notes: `references/book-summary.md`
(read only if the user asks about the book itself).

## The one idea

> "The secret of good writing is to strip every sentence to its cleanest components."

Clear writing is clear thinking made visible. Before each sentence ask *What am I trying to
say?* After it ask *Have I said it? Would someone meeting this subject for the first time
understand it?* Then cut. Most first drafts lose half their words with no loss of meaning.

## Rules, with examples and counterexamples

### 1. Cut clutter
Bracket every word that does no work and read the sentence without it. If it still works, the
word goes.

| Clutter | Plain |
|---|---|
| at this point in time, currently, at the present time | now |
| due to the fact that | because |
| with the possible exception of | except |
| until such time as | until |
| for the purpose of | for |
| he totally lacked the ability to | he couldn't |
| in order to | to |
| assistance / numerous / facilitate / implement / sufficient / attempt / utilize / referred to as | help / many / ease / do / enough / try / use / called |
| head up, face up to, free up, order up | head, face, free, order |
| a personal friend, his personal feeling | a friend, his feeling |
| Are you experiencing any pain? | Does it hurt? |

Throat-clearing to delete outright: *It should be noted that*, *It is interesting to note*,
*I might add*, *It's worth mentioning*, *Note that*, *In other words*, *Basically*. Say the
thing.

Redundant modifiers: *blared loudly*, *clenched tightly*, *tall skyscraper*, *completely
finished*, *end result*, *fully verified*. The noun or verb already says it.

- ✗ "In order to facilitate the migration process, we utilized a helper that is referred to as `copyState`."
- ✓ "To ease the migration we used a helper called `copyState`."

### 2. Prefer short words and short sentences
Lincoln's Second Inaugural: 505 of 701 words are one syllable. Long words signal "a ponderous
mind is at work" and readers stop before they start.

- ✗ Orwell's parody: "Objective consideration of contemporary phenomena compels the conclusion that success or failure in competitive activities exhibits no tendency to be commensurate with innate capacity."
- ✓ Ecclesiastes: "The race is not to the swift, nor the battle to the strong."

### 3. One thought per sentence
"Readers can process only one idea at a time, and they do it in linear sequence." A tangled
sentence usually holds two thoughts. Split it. Never fear a two- or three-sentence run of
short declaratives.

- ✗ "The cache, which had been introduced to reduce RPC load but was never invalidated on reorgs, caused stale reads that surfaced as flaky tests, so this PR adds invalidation."
- ✓ "The cache was added to reduce RPC load. It was never invalidated on reorgs. Stale reads followed, and they showed up as flaky tests. This PR adds the invalidation."

### 4. Use active verbs; name the actor
"Joe saw him" beats "He was seen by Joe." Passives hide who did what. Pick the precise verb:
not "stepped down" when you mean "was fired"; not "handles" when you mean "retries", "drops",
or "logs".

- ✗ "An error is thrown when the block is not found."
- ✓ "The syncer throws when it cannot find the block."

### 5. Replace concept nouns with people doing things
Abstract nouns plus *is/isn't* make dead sentences. Creeping nounism stacks nouns where a
verb belongs.

- ✗ "The common reaction is incredulous laughter." → ✓ "Most people just laugh with disbelief."
- ✗ "thunderstorm probability situation" → ✓ "it's going to rain"
- ✗ "Capacity planning adds objectivity to the decision-making process." → ✓ "You should know the facts before you decide."
- ✗ "The system is delivered with functionality." → ✓ "It works."

### 6. Kill hedges and qualifiers; commit
*a bit, sort of, kind of, rather, quite, very, somewhat, fairly, arguably, generally,
potentially, it seems, I think, it remains to be seen.* "Don't be kind of bold. Be bold."
Elliot Richardson's "on balance, affirmative action has, I think, been a qualified success"
hedges five times in thirteen words. If you are unsure, say what you know and what you
don't, in one plain sentence each.

- ✗ "This should probably fix the issue in most cases, I think."
- ✓ "This fixes the race for a single writer. Two concurrent writers can still collide; see the note in the test."

### 7. Drop adjectives that state the obvious or hype
Cut *precipitous cliffs, lacy spiderwebs, yellow daffodils*. In our domain cut *robust,
powerful, seamless, elegant, comprehensive, cutting-edge, simple* (if it were simple you
wouldn't say so). Keep an adjective only when it carries a judgment the reader needs.
"Choose your words with unusual care. If a phrase comes to you easily, look at it with deep
suspicion."

### 8. Trust your material; don't pre-react for the reader
Cut *surprisingly, interestingly, importantly, of course, notably, crucially*. Let a striking
fact land bare. "Mali got its independence in 1960. We were in Timbuktu for an event that
hadn't been held in 27 years." No exclamation point. Never overstate; one caught
exaggeration makes everything else suspect.

### 9. Avoid journalese, fad words, and stale metaphors
*leverage, utilize, dialogue* (verb), *interface* (verb), *prioritize, paradigm,
synergy, robust, streamline, empower, ecosystem, journey, deep dive, under the hood,
at the end of the day, moving forward.* Use the plain word every time, and repeat it
rather than hunt for a synonym: "The cure is worse than the ailment."

### 10. Write the way you would talk, in one voice
"Never say anything in writing that you wouldn't comfortably say in conversation." No
*indeed, moreover, thus, hence, furthermore, one finds oneself, it is to be hoped that*.
Use contractions. Use "I" and "you". Two failure modes, equally bad:

- **Pompous**: "Fundamentally, Foster is a good school. In the school year ahead we seek to provide enhanced positive learning environments." (nobody home)
- **Breezy**: "Ever stay up late babysitting a sick porker? Believe you me, a guy can lose a heckuva lot of shut-eye." (crude, corny, condescending)
- **Right**: "I have met many of you in the first few weeks. Please continue to stop in to introduce yourself." (a person, talking)

Never talk down. "Readers will stop reading you if they think you are talking down to them."
Keep pronoun, tense and tone consistent through the whole piece.

### 11. Explain like the reader knows nothing: the upside-down pyramid
For any technical explanation: "Start at the bottom with the one fact a reader must know
before he can learn any more." Each sentence broadens the one before. After every sentence
ask *what does the reader want to know next?* and answer exactly that. Relate the unfamiliar
to something the reader can picture. Define a term the moment you use it, in a few words,
rather than avoiding it. Keep a person in the story: who is affected, who does what.

- ✗ "Sub-system support is available only with VSAG or TNA."
- ✓ A customer's line Zinsser praised: "A computer is like a sophisticated pencil. You don't care how it works, but if it breaks you want someone there to fix it."

### 12. Lead with the point; stop when you're done
"The most important sentence in any article is the first one." Open with the fact, the
result, or the surprise, never with scene-setting or a restatement of the question. Make
each paragraph's last sentence a springboard into the next. End when the material ends. No
"In summary", no recap of what you just said, no closing pleasantry.

- ✗ "In this PR, I set out to address the issue that was raised regarding..."
- ✓ "Reorgs left stale entries in the block cache. This PR invalidates them."

### 13. Think small; make one point
"Nobody can write a book or an article 'about' something." Decide what the piece is
*really* about and cut everything else, however fond you are of it. "Readers should always
feel that you know more about your subject than you've put in writing."

### 14. Mechanics
- Start sentences with *But*. Put *however* mid-sentence, never first or last.
- Signal a turn early with a short word: *but, yet, still, instead, now, later, meanwhile*. "Yet he decided to go" replaces "Despite the fact that all these dangers had been pointed out to him, he decided to go."
- Prefer the period. Use the dash to amplify or to set off an aside. Use the colon before a list. Use semicolons and exclamation points almost never.
- Default to *that*; use *which* only after a comma. "Take the shoes that are in the closet" vs. "Take the shoes, which are in the closet."
- Put the word that matters at the end of the sentence; it is what stays in the reader's ear.
- Short paragraphs, but not a stutter of one-liners. Each paragraph holds one unit of thought.
- Watch what the last noun points to: "The tragic hero of the play is Othello. Small and malevolent, Iago feeds his jealous suspicions." reads as if Othello is small and malevolent.

## The rewrite pass (run before sending)

Read the draft as the reader would, tracking what they know at each point. Zinsser's checklist
for a first draft: "It's not clear. It's not logical. It's verbose. It's klunky. It's
pretentious. It's boring. It's full of clutter. It's full of clichés. It lacks rhythm. It can be
read in several different ways. It doesn't lead out of the previous sentence."

1. First sentence: does it carry the point? If not, delete everything above the sentence that does.
2. Every sentence: one thought? active verb? named actor? Could it be two sentences?
3. Every word: bracket it. Clutter phrases, hedges, intensifiers, throat-clearing, hype adjectives, pre-reactions. Cut.
4. Every term: would a newcomer know it? Define in place or replace.
5. Read aloud in your head. Does it sound like a person talking, neither stiff nor chummy?
6. Ending: does it stop, or does it summarize? Cut the summary.
7. When a sentence keeps fighting you, ask "Do I need it at all?" Deletion is the quickest fix.

"Be grateful for everything you can throw away."
