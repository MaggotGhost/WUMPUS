import unittest

from Wumpus import Agente, Mundo, vecinos


class MundoTests(unittest.TestCase):
    def test_classic_world_is_solved(self):
        agent = Agente(Mundo())

        for _ in range(100):
            if not agent.vivo or agent.fin:
                break
            agent.paso()

        self.assertTrue(agent.oro)
        self.assertTrue(agent.vivo)
        self.assertTrue(agent.fin)
        self.assertEqual(agent.pos, (1, 1))
        self.assertTrue(any("escapo" in texto.lower() for _, texto in agent.log))

    def test_no_exit_scenario_has_no_safe_first_move(self):
        world = Mundo(sin_salida=True)
        exits = set(vecinos((1, 1)))

        self.assertEqual(exits, world.hoyos)
        self.assertFalse(world._resoluble())

        agent = Agente(world)
        agent.paso()

        self.assertFalse(agent.vivo)
        self.assertTrue(agent.fin)
        self.assertFalse(agent.oro)

    def test_world_modes_cannot_be_combined(self):
        with self.assertRaises(ValueError):
            Mundo(aleatorio=True, sin_salida=True)


if __name__ == "__main__":
    unittest.main()
