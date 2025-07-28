import { Command } from 'commander';
import { updateProfile, showProfile } from '../agents/profile_agent';
import { logger } from '../utils/logger';

export const profileCommand = new Command('profile')
  .description('ユーザープロファイルを管理するコマンド')
  .addCommand(
    new Command('update')
      .description('職務経歴書ファイルからプロファイルを更新します')
      .option('--cv <path>', '職務経歴書のファイルパス')
      .option('--plan <path>', 'キャリアプランのファイルパス')
      .action(async (options) => {
        if (!options.cv) {
          logger.error('エラー: --cv オプションで職務経歴書のパスを指定してください。');
          return;
        }
        await updateProfile(options.cv, options.plan);
      }),
  )
  .addCommand(
    new Command('show').description('現在のプロファイル情報を表示します').action(async () => {
      const profile = await showProfile();
      logger.log(profile);
    }),
  );
