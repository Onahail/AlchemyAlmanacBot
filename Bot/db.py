import os
import dotenv
import asyncpg
import traceback
from collections import defaultdict

dotenv.load_dotenv()
DB_PASS = os.getenv("DB_PASS")

class Database:
    """Provides an interface to the inventory/recipe database"""

    def __init__(self):
        self.pool = None
        self.regions = []
        self.creatures = []
        self.components = []
        self.medicines = []
        self.alchemical_items = []
        self.discord_members = []

    async def connect(self):
        print("[DB] Connecting...")
        self.pool = await asyncpg.create_pool(
            user='postgres',
            password=DB_PASS,
            database='botdb',
            host='localhost',
            port=5432,
            min_size=1,
            max_size=5
        )

    async def init_utils(self):
        self.regions = await self.get_all_regions()
        self.creatures = await self.get_all_creatures()
        self.components = await self.get_all_components()
        self.medicines = await self.get_all_medicines()
        self.alchemical_items = await self.get_all_alchemy()

    async def register_new_server(self, discord_server_id):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO servers (server_id) VALUES ($1);", discord_server_id)

    async def remove_server(self, db_unique_server_id: int):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("DELETE FROM dms WHERE server_id = $1;", db_unique_server_id)
                await conn.execute("DELETE FROM players WHERE server_id = $1;", db_unique_server_id)
                await conn.execute("DELETE FROM servers WHERE id = $1;", db_unique_server_id)

    async def get_server_database_id(self, discord_server_id) -> int:
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT id FROM servers WHERE server_id = $1", discord_server_id
            )
            return result["id"] if result else 0

    async def get_server_id_from_database_id(self, db_unique_server_id) -> int:
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT server_id FROM servers WHERE id = $1", db_unique_server_id
            )
            return result["server_id"] if result else 0

    async def get_player_database_id(self, discord_user_id, db_unique_server_id) -> int:
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT id FROM players WHERE user_id = $1 AND server_id = $2", discord_user_id, db_unique_server_id
            )
            return result["id"] if result else 0

    async def get_user_id_from_database_id(self, db_unique_user_id, db_unique_server_id) -> int:
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT user_id FROM players WHERE id = $1 AND server_id = $2", db_unique_user_id, db_unique_server_id
            )
            return result["user_id"] if result else 0

    async def get_all_players(self, server_id: int) -> list[dict[str, any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM players WHERE server_id = $1;", server_id)
            return [dict(row) for row in rows]

    async def get_player(self, db_unique_player_id: int, server_id: int) -> dict:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM players WHERE id = $1 AND server_id = $2;", db_unique_player_id, server_id)
            return dict(row) if row else {}

    async def register_player(self, discord_user_id: int, server_id: int, character_name: str) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO players (user_id, character_name, server_id) VALUES ($1, $2, $3);",
                discord_user_id, character_name, server_id
            )

    async def deregister_player(self, db_unique_player_id: int, server_id: int) -> None:
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """
                    DELETE FROM player_inventories 
                    WHERE player_id = (SELECT id FROM players WHERE id = $1);
                    """,
                    db_unique_player_id
                )
                await conn.execute("DELETE FROM players WHERE id = $1 AND server_id = $2;", db_unique_player_id, server_id)

    async def get_server_dm(self, server_id) -> dict:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM dms WHERE server_id = $1", server_id)
            return dict(row) if row else {}

    async def register_dm(self, discord_user_id: int, server_id: int) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO dms (server_id, user_id)
                VALUES ($1, $2)
                ON CONFLICT (server_id) DO UPDATE SET user_id = EXCLUDED.user_id;
                """,
                server_id, discord_user_id
            )

    async def deregister_dm(self, discord_user_id: int, server_id: int) -> None:
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    "DELETE FROM dms WHERE user_id = $1 AND server_id = $2", discord_user_id, server_id)

    async def get_player_inventory(self, db_unique_player_id: int) -> list[dict[str, any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT c.id, c.name, c.display_name, pi.component_quantity AS quantity
                FROM players p
                JOIN player_inventories pi ON p.id = pi.player_id
                JOIN components c ON pi.component_id = c.id
                WHERE p.id = $1;
                """,
                db_unique_player_id
            )
            return [dict(row) for row in rows] if rows else {}

    async def add_player_inventory_item(self, db_unique_player_id: int, component_name: str, amount: int) -> None:
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """
                    UPDATE player_inventories
                    SET component_quantity = component_quantity + $1
                    WHERE player_id = (SELECT id FROM players WHERE id = $2)
                    AND component_id = (SELECT id FROM components WHERE name = $3);
                    """,
                    amount, db_unique_player_id, component_name
                )
                await conn.execute(
                    """
                    INSERT INTO player_inventories (player_id, component_id, component_quantity)
                    SELECT (SELECT id FROM players WHERE id = $1),
                           (SELECT id FROM components WHERE name = $2),
                           $3
                    WHERE NOT EXISTS (
                        SELECT 1 FROM player_inventories
                        WHERE player_id = (SELECT id FROM players WHERE id = $1)
                        AND component_id = (SELECT id FROM components WHERE name = $2)
                    );
                    """,
                    db_unique_player_id, component_name, amount
                )
                await self._clean_inventory_table()

    async def sub_player_inventory_item(self, db_unique_player_id: int, component_name: str, amount: int) -> None:
        await self.add_player_inventory_item(db_unique_player_id, component_name, -amount)

    async def delete_player_inventory_item(self, db_unique_player_id: int, component_name: str) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                DELETE FROM player_inventories
                WHERE player_id = (SELECT id FROM players WHERE id = $1)
                AND component_id = (SELECT id FROM components WHERE name = $2);
                """,
                db_unique_player_id, component_name
            )

    async def _clean_inventory_table(self) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM player_inventories WHERE component_quantity < 1;")

    async def get_medicine_recipe(self, name: str) -> list[list[dict[str, any]]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT rc.component_number, m.name AS recipe, c.id, c.name, c.display_name,
                       rc.component_quantity AS quantity, rc.rank_quantity
                FROM medicines m
                JOIN medicine_recipes rc ON m.id = rc.medicine_id
                JOIN components c ON rc.component_id = c.id
                WHERE m.name = $1
                ORDER BY rc.component_number;
                """,
                name
            )
            grouped = defaultdict(list)
            for row in rows:
                grouped[row["component_number"]].append(dict(row))
            return list(grouped.values())

    async def get_alchemy_recipe(self, name: str) -> list[list[dict[str, any]]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT rc.component_number, m.name AS recipe, c.id, c.name, c.display_name,
                       rc.component_quantity AS quantity
                FROM alchemical_items m
                JOIN alchemical_recipes rc ON m.id = rc.item_id
                JOIN components c ON rc.component_id = c.id
                WHERE m.name = $1
                ORDER BY rc.component_number;
                """,
                name
            )
            grouped = defaultdict(list)
            for row in rows:
                grouped[row["component_number"]].append(dict(row))
            return list(grouped.values())

    async def get_medicine_description(self, name: str) -> str:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT description FROM medicines WHERE name = $1;", name)
            return row["description"] if row else "Description not found."

    async def get_alchemy_description(self, name: str) -> str:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT description FROM alchemical_items WHERE name = $1;", name)
            return row["description"] if row else "Description not found."

    async def get_special_requirements(self, name: str) -> str:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT special_requirements FROM alchemical_items WHERE name = $1;", name)
            return row["special_requirements"] if row else "Description not found."

    async def get_medicine_strength(self, name: str) -> str:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT strength FROM medicines WHERE name = $1;", name)
            return row["strength"] if row else "Description not found."

    async def get_medicine_stats(self, name: str) -> list[dict[str, any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT boost, boost_amt, can_infinite, duration, dice, rank_values
                FROM medicines
                WHERE name = $1;
                """,
                name
            )
            return [dict(row) for row in rows] if rows else None

    async def get_alchemy_strength(self, name: str) -> str:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT strength FROM alchemical_items WHERE name = $1;", name)
            return row["strength"] if row else "Description not found."

    async def get_player_possible_medicines(self, db_unique_player_id: int) -> list[dict[str, any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                WITH player_inventory AS (
                    SELECT p.id AS player_id, pi.component_id, pi.component_quantity
                    FROM players p
                    JOIN player_inventories pi ON p.id = pi.player_id
                    WHERE p.id = $1
                ),
                required_components AS (
                    SELECT mr.medicine_id, mr.component_id, mr.component_number, mr.component_quantity
                    FROM medicine_recipes mr
                ),
                player_component_quantities AS (
                    SELECT rc.medicine_id, rc.component_number,
                           COALESCE(SUM(pi.component_quantity), 0) AS player_total_quantity
                    FROM required_components rc
                    LEFT JOIN player_inventory pi ON rc.component_id = pi.component_id
                    GROUP BY rc.medicine_id, rc.component_number
                ),
                sufficient_components AS (
                    SELECT rc.medicine_id, rc.component_number, rc.component_quantity,
                           COALESCE(pcg.player_total_quantity, 0) AS player_total_quantity
                    FROM required_components rc
                    LEFT JOIN player_component_quantities pcg
                    ON rc.medicine_id = pcg.medicine_id AND rc.component_number = pcg.component_number
                ),
                craftable_medicines AS (
                    SELECT medicine_id, FLOOR(MIN(player_total_quantity / component_quantity)) AS max_crafts
                    FROM sufficient_components
                    GROUP BY medicine_id
                    HAVING FLOOR(MIN(player_total_quantity / component_quantity)) > 0
                )
                SELECT m.*, cm.max_crafts
                FROM craftable_medicines cm
                JOIN medicines m ON cm.medicine_id = m.id;
            """, db_unique_player_id)

        medicines = [dict(row) for row in rows]

        # ✅ Add recipes using await for each medicine
        for medicine in medicines:
            medicine["recipe"] = await self.get_medicine_recipe(medicine["name"])

        return medicines

    async def get_player_possible_alchemy(self, db_unique_player_id: int) -> list[dict[str, any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                WITH player_inventory AS (
                    SELECT p.id AS player_id, pi.component_id, pi.component_quantity
                    FROM players p
                    JOIN player_inventories pi ON p.id = pi.player_id
                    WHERE p.id = $1
                ),
                required_components AS (
                    SELECT ar.item_id, ar.component_id, ar.component_number, ar.component_quantity
                    FROM alchemical_recipes ar
                ),
                player_component_quantities AS (
                    SELECT rc.item_id, rc.component_number,
                           COALESCE(SUM(pi.component_quantity), 0) AS player_total_quantity
                    FROM required_components rc
                    LEFT JOIN player_inventory pi ON rc.component_id = pi.component_id
                    GROUP BY rc.item_id, rc.component_number
                ),
                sufficient_components AS (
                    SELECT rc.item_id, rc.component_number, rc.component_quantity,
                           COALESCE(pcg.player_total_quantity, 0) AS player_total_quantity
                    FROM required_components rc
                    LEFT JOIN player_component_quantities pcg
                    ON rc.item_id = pcg.item_id AND rc.component_number = pcg.component_number
                ),
                craftableitems AS (
                    SELECT item_id, FLOOR(MIN(player_total_quantity / component_quantity)) AS max_crafts
                    FROM sufficient_components
                    GROUP BY item_id
                    HAVING FLOOR(MIN(player_total_quantity / component_quantity)) > 0
                )
                SELECT ai.*, ci.max_crafts
                FROM craftableitems ci
                JOIN alchemical_items ai ON ci.item_id = ai.id;
            """, db_unique_player_id)

        items = [dict(row) for row in rows]

        for item in items:
            item["recipe"] = await self.get_alchemy_recipe(item["name"])

        return items

    async def player_can_craft_medicine(self, db_unique_player_id: int, medicine_name: str) -> bool:
        medicines = await self.get_player_possible_medicines(db_unique_player_id)
        return medicine_name in [m["name"] for m in medicines]

    async def player_can_craft_alchemy(self, db_unique_player_id: int, alchemy_name: str) -> bool:
        items = await self.get_player_possible_alchemy(db_unique_player_id)
        return alchemy_name in [i["name"] for i in items]

    async def get_components_by_region(self, name: str) -> list[dict[str, any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT c.id, c.name, c.display_name, rc.dc
                FROM components c
                JOIN region_components rc ON c.id = rc.component_id
                JOIN regions r ON rc.region_id = r.id
                WHERE r.name = $1
                ORDER BY rc.dc;
                """,
                name
            )
            return [dict(row) for row in rows]

    async def get_components_by_creature_base(self, name: str) -> list[dict[str, any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT c.id, c.name, c.display_name, cr.creature_name, cr.creature_base, cc.amount, cc.dc
                FROM creature_components cc
                JOIN components c ON cc.component_id = c.id
                JOIN creatures cr ON cc.creature_id = cr.id
                WHERE cr.creature_base = $1
                ORDER BY cr.creature_name, cc.dc;
                """,
                name
            )
            return [dict(row) for row in rows]

    async def get_components_by_creature_name(self, base: str, name: str) -> list[dict[str, any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT c.id, c.name, c.display_name, cr.creature_name, cr.creature_base, cc.amount, cc.dc
                FROM creature_components cc
                JOIN components c ON cc.component_id = c.id
                JOIN creatures cr ON cc.creature_id = cr.id
                WHERE cr.creature_base = $1 AND cr.creature_name = $2
                ORDER BY cr.creature_name, cc.dc;
                """,
                base, name
            )
            return [dict(row) for row in rows]

    async def get_creatures_by_creature_base(self, name: str) -> list[dict[str, any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT cr.id, cr.creature_name FROM creatures cr WHERE cr.creature_base = $1;",
                name
            )
            return [dict(row) for row in rows]

    async def get_creature_by_name(self, base: str, name: str) -> list[dict[str, any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM creatures WHERE creature_base = $1 AND creature_name = $2;",
                base, name
            )
            return [dict(row) for row in rows]

    async def get_component_source(self, name: str) -> list[dict[str, any]]:
        async with self.pool.acquire() as conn:
            creature = await conn.fetch(
                """
                SELECT cc.component_id, c.name, c.display_name, cc.amount, cr.creature_name AS source_name,
                       'Creature' AS source_type, cr.creature_base AS source_detail, cc.dc AS roll
                FROM creature_components cc
                JOIN components c ON cc.component_id = c.id
                JOIN creatures cr ON cc.creature_id = cr.id
                WHERE c.name = $1;
                """,
                name
            )
            regions = await conn.fetch(
                """
                SELECT rc.component_id, c.name, c.display_name, NULL AS amount, r.name AS source_name,
                       'Region' AS source_type, NULL AS source_detail, rc.dc AS roll
                FROM region_components rc
                JOIN components c ON rc.component_id = c.id
                JOIN regions r ON rc.region_id = r.id
                WHERE c.name = $1;
                """,
                name
            )
            common = await conn.fetch(
                """
                SELECT ct.component_id, c.name, c.display_name, NULL AS amount, ct.type AS source_name,
                       'CommonTable' AS source_type, NULL AS source_detail, ct.roll AS roll
                FROM common_tables ct
                JOIN components c ON ct.component_id = c.id
                WHERE c.name = $1;
                """,
                name
            )
            merchant = await conn.fetch(
                """
                SELECT mc.component_id, c.name, c.display_name, mc.cost AS amount, NULL AS source_name,
                       'Merchant' AS source_type, mc.availability AS source_detail, NULL AS roll
                FROM merchant_components mc
                JOIN components c ON mc.component_id = c.id
                WHERE c.name = $1;
                """,
                name
            )
            return [dict(row) for row in creature + regions + common + merchant]

    async def get_component_recipes(self, name: str) -> list[dict[str, any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT c.display_name, m.display_name AS medicine, a.display_name AS alchemy
                FROM components c
                LEFT JOIN medicine_recipes mr ON mr.component_id = c.id
                LEFT JOIN medicines m ON m.id = mr.medicine_id
                LEFT JOIN alchemical_recipes ar ON ar.component_id = c.id
                LEFT JOIN alchemical_items a ON a.id = ar.item_id
                WHERE c.name = $1;
                """,
                name
            )
            return [dict(row) for row in rows]

    async def get_boosted_recipes_by_component(self, name: str) -> list[dict[str, any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT m.display_name FROM medicines m WHERE m.boost = $1;",
                name
            )
            return [dict(row) for row in rows]

    async def get_common_tables(self, table_type: str) -> list[dict[str, any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT ct.component_id, c.name, c.display_name, ct.roll AS roll
                FROM common_tables ct
                JOIN components c ON ct.component_id = c.id
                WHERE ct.type = $1;
                """,
                table_type
            )
            return [dict(row) for row in rows]

    async def get_component_by_name(self, name: str) -> dict:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM components WHERE name = $1;", name)
            return dict(row) if row else {}

    async def get_region_by_name(self, name: str) -> dict:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM regions WHERE name = $1;", name)
            return dict(row) if row else {}

    async def get_all_medicines(self) -> list[dict[str, any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM medicines;")
            return [dict(row) for row in rows]

    async def get_medicine_by_name(self, name: str) -> dict:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM medicines WHERE name = $1;", name)
            return dict(row) if row else {}

    async def get_all_alchemy(self) -> list[dict[str, any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM alchemical_items;")
            return [dict(row) for row in rows]

    async def get_alchemy_by_name(self, name: str) -> dict:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM alchemical_items WHERE name = $1;", name)
            return dict(row) if row else {}

    async def get_all_components(self) -> list[dict[str, any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM components;")
            return [dict(row) for row in rows]

    async def get_all_creatures(self) -> list[dict[str, any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM creatures;")
            return [dict(row) for row in rows]

    async def get_all_regions(self) -> list[dict[str, any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM regions;")
            return [dict(row) for row in rows]


db = Database()
