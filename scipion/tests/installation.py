import unittest
from scipion.install.funcs import CommandDef, CondaCommandDef

class TestCommands(unittest.TestCase):
    def test_command_class(self):

        myCmd = CommandDef("ls -l", "lolo")\
            .append("cd ..", ["one", "two"])\
            .append("cd .", sep="?")

        self.assertEqual(myCmd.getCommands()[0][0], "ls -l && cd .. ? cd .")
        self.assertEqual(myCmd.getCommands()[0][1], ["lolo", "one", "two"])

        cmds = CondaCommandDef("modelangelo-3.0")
        cmds.create('python=3.9').activate().cd('model-angelo')\
            .pipInstall('-r requirements.txt')\
            .condaInstall('-y torchvision torchaudio cudatoolkit=11.3 -c pytorch')\
            .pipInstall('-e .').touch('../env-installed.txt')

        print(cmds.getCommands())


if __name__ == '__main__':
    unittest.main()
