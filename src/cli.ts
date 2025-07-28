import { Command } from 'commander';
import { profileCommand } from './commands/profile';

const program = new Command();

program.version('0.1.0').description('キャリアプランニングを支援するCLIツール');

program.addCommand(profileCommand);

program.parse(process.argv);
