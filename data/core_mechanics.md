# Hypixel Skyblock — Core Mechanics Reference

## Auction House (AH)

- Players can list items as BIN (Buy It Now) auctions
- Maximum 14 active listings per player at once
- Listings last up to 14 days; unsold items can be reclaimed
- **Listing fee** (paid upfront, non-refundable):
  - < 10M coins: 1% of listing price
  - 10M–100M coins: 2% of listing price
  - > 100M coins: 2.5% of listing price
- **Claiming fee** (deducted when collecting sold coins):
  - 1% for items that sold above 1M coins
  - During Derpy mayor: 4% instead of 1%
- Items below 1M coins have no claiming fee
- Bundle flipping: buying multi-item stacks cheaper per unit than singles, then reselling individually

## Bazaar

- Instant buy/sell marketplace for stackable items
- No listing fee — but prices are competitive and constantly updating
- Buy orders: place an order at a set price, fulfilled when sellers match
- Sell offers: list at a price, buyers can fill instantly
- Bazaar prices fluctuate rapidly; best used as a price floor reference, not a guaranteed exit

## Coins & Wealth

- **Purse**: coins carried on the player, lost on death (unless protected)
- **Bank**: coins stored safely in the co-op island bank, shared across co-op members
- **Co-op bank**: shared between all members of a co-op profile
- Total liquid wealth = purse + bank balance
- Items in inventory, enderchest, and backpacks have indirect value (must be sold first)

## Mayor System

- A new mayor is elected every Skyblock year (~5 real days)
- Each mayor has unique perks that affect game mechanics
- **Derpy**: QUAD TAXES — claiming fee on sold AH items becomes 4% (only affects items sold above 1M coins)
- Other mayors do not affect AH taxes
- Current mayor is returned by the Hypixel election API

## Item Rarity

Rarities from lowest to highest: COMMON → UNCOMMON → RARE → EPIC → LEGENDARY → MYTHIC → DIVINE → SPECIAL → VERY SPECIAL
- Higher rarity generally means higher value and lower supply
- LEGENDARY pets and items are often the most traded

## Pets

- Pets have levels (1–100) and rarities
- Higher level and rarity = significantly higher value
- Pets can be leveled using Pet XP items
- Some pets are extremely valuable (e.g. Golden Dragon, Ender Dragon)

## Enchantments & Upgrades

- Items can be enchanted using the Enchantment Table or Anvil
- Ultimate enchants (e.g. Ultimate Wise, Ultimate Jerry) are rare and very valuable
- Recombobulator 3000 upgrades item rarity by one tier — massively increases value
- Stars (Dungeon/Crimson Isle): items can be upgraded with stars, each star increases stats and value

## Dungeon Items

- Found in The Catacombs dungeon
- Have a special "essence" upgrade system
- Floor-specific items are highly sought after
- Master Mode variants are rarer and more valuable

## Daily Limits

- Some Bazaar items have daily purchase limits (e.g. Enchanted items from NPCs)
- NPC shops also have daily limits — buying at NPC price and selling on AH can be profitable when there's a spread
