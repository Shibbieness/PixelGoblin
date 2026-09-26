# Build a city from a list of names

You have a list of names, and you want every one of them to be a character who always looks the same, has a job, belongs to a family, and stands somewhere in the village.

## 1. Write the names

One citizen per line, in a text file:

```
Grubnak Ashfang : blacksmith
Mizzle Ashfang : craftswoman
Tok Ashfang
Pip Ashfang
Old Pell Reedwhistle : elder_scholar
Nib Reedwhistle (child)
Quib
```

- **A shared last name is a household.** Its first two grown members are the parents. Later members are their children, and they inherit face, hair and build from the parents.
- **`: blacksmith`** pins a job. Without it, the job is drawn from the city's census weights.
- **`(child)`**, **`(elder)`** or **`(adult)`** says who is young or old.
- A line starting with `#` is a comment.

## 2. Pick (or write) a city file

`flavors/boc/village/goblintown.city.toml` holds the rules the names are dealt from:

| Table | What it sets |
|---|---|
| `scene` | the village the citizens stand in |
| `[census]` | job weights for grown citizens (weights, not quotas) |
| `[children]`, `[elders]` | jobs for the young and the old |
| `[subspecies]` | subspecies weights, drawn once per household |
| `clans` | clan colours, drawn once per household; a household named after a clan (House Ashfang) belongs to it |
| `[bands]` | how likely a citizen is to stand far, in the middle, or near |

## 3. Run it

```
pixelgoblin city boc.city.goblintown names.txt --out town/
```

You get:

- `census.json`: every citizen's name, seed, job, subspecies, clan, household, parents, and what they inherited from whom;
- `citizens.png`: everyone, household by household;
- `village.png`: the village with them in it. Each depth band holds as many citizens as the scene's crowd count. Anyone who doesn't fit is **indoors**, and the census says so.

In the workbench, the **City** tab does the same thing live: paste names, press **Build the city**, and click anyone to see them at every size and from three sides.

## What stays fixed

Each citizen is decided by their own name and the city file, nothing else. So:

- the same list always makes the same city;
- adding a name never changes anyone else, except that a new member of a household becomes its newest child;
- removing a name never changes anyone else;
- editing the city file changes everyone, which is correct, because the rules changed.

Gate B19 checks all of this.

—Shibbieness
—Claude
