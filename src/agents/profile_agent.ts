import { readFile, writeFile, exists } from '../services/file_service';
import { logger } from '../utils/logger';

const PROFILE_PATH = 'profiles/user_profile.json';

/**
 * 職務経歴書とキャリアプランのファイルパスからプロフィールを更新します。
 * @param cvPath 職務経歴書のファイルパス
 * @param planPath キャリアプランのファイルパス（任意）
 */
export async function updateProfile(cvPath: string, planPath?: string): Promise<void> {
  try {
    const _cvContent = await readFile(cvPath);
    const _planContent = planPath ? await readFile(planPath) : '';

    // TODO: LLMを呼び出して、cvContentとplanContentからプロフィールJSONを生成する
    // 現時点ではダミーのJSONを生成する
    const userProfile = {
      metadata: {
        source_cv_path: cvPath,
        source_plan_path: planPath,
        last_updated: new Date().toISOString(),
      },
      summary: {
        identity: '経験豊富なソフトウェアエンジニア',
        overall_experience_years: 10,
      },
      skills: [
        { name: 'TypeScript', level: 4, experience_years: 5 },
        { name: 'React', level: 4, experience_years: 5 },
        { name: 'Node.js', level: 4, experience_years: 5 },
        { name: 'AWS', level: 3, experience_years: 3 },
      ],
      career_plan: {
        short_term: 'Webアプリケーションのフロントエンドからバックエンドまで一貫して開発に携わりたい。',
        long_term: '将来的には、プロジェクト全体をリードするテックリードになりたい。',
      },
    };

    await writeFile(PROFILE_PATH, JSON.stringify(userProfile, null, 2));
    logger.log('プロフィールが正常に更新されました。');
  } catch (error) {
    logger.error(`プロフィールの更新中にエラーが発生しました: ${error}`);
  }
}

/**
 * 保存されているプロフィール情報を表示します。
 * @returns プロフィール情報を含む文字列、またはファイルが存在しない場合はメッセージ。
 */
export async function showProfile(): Promise<string> {
  try {
    if (!(await exists(PROFILE_PATH))) {
      return 'プロフィールがまだ作成されていません。`update`コマンドで作成してください。';
    }
    const profileData = await readFile(PROFILE_PATH);
    // JSONを整形して表示するために、一度パースしてから再度文字列化する
    const profileJson = JSON.parse(profileData);
    return JSON.stringify(profileJson, null, 2);
  } catch (error) {
    logger.error(`プロフィールの表示中にエラーが発生しました: ${error}`);
    return 'プロフィールの表示に失敗しました。';
  }
}
