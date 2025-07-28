import { promises as fs } from 'fs';

/**
 * 指定されたパスのファイルを読み込み、その内容を文字列として返します。
 * @param filePath 読み込むファイルの絶対パスまたは相対パス。
 * @returns ファイルの内容を解決するPromise。
 */
export async function readFile(filePath: string): Promise<string> {
  try {
    return await fs.readFile(filePath, 'utf-8');
  } catch (error) {
    console.error(`Error reading file from path: ${filePath}`, error);
    throw error;
  }
}

/**
 * 指定されたパスにファイルを作成し、内容を書き込みます。
 * @param filePath 書き込むファイルの絶対パスまたは相対パス。
 * @param content ファイルに書き込む内容。
 */
export async function writeFile(filePath: string, content: string): Promise<void> {
  try {
    await fs.writeFile(filePath, content, 'utf-8');
  } catch (error) {
    console.error(`Error writing file to path: ${filePath}`, error);
    throw error;
  }
}

/**
 * 指定されたパスにファイルが存在するかどうかを確認します。
 * @param filePath 確認するファイルの絶対パスまたは相対パス。
 * @returns ファイルが存在する場合はtrue、そうでない場合はfalseを解決するPromise。
 */
export async function exists(filePath: string): Promise<boolean> {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}
