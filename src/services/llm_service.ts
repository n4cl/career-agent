import { ChatGoogleGenerativeAI } from '@langchain/google-genai';
import { PromptTemplate } from '@langchain/core/prompts';
import { JsonOutputParser } from '@langchain/core/output_parsers';
import { logger } from '../utils/logger';

/**
 * LLMとの連携を担当するサービスクラス
 */
export class LLMService {
  private model: ChatGoogleGenerativeAI;

  constructor() {
    this.model = new ChatGoogleGenerativeAI({
      apiKey: process.env.GEMINI_API_KEY,
      model: 'gemini-flash',
      temperature: 0,
    });
  }

  /**
   * プロンプトと入力変数を受け取り、LLMからJSON形式の応答を生成します。
   * @param promptTemplateText プロンプトテンプレートの文字列
   * @param inputVariables プロンプトに挿入するキーと値のペア
   * @returns 生成されたJSONオブジェクト
   */
  async generateJson<T extends object>(
    promptTemplateText: string,
    inputVariables: Record<string, unknown>,
  ): Promise<T> {
    try {
      const parser = new JsonOutputParser<T>();

      const promptTemplate = new PromptTemplate({
        template: promptTemplateText,
        inputVariables: Object.keys(inputVariables),
        partialVariables: { format_instructions: parser.getFormatInstructions() },
      });

      const chain = promptTemplate.pipe(this.model).pipe(parser);

      logger.log('LLMへのリクエストを開始します...');
      const result = await chain.invoke(inputVariables);
      logger.log('LLMからの応答を受信しました。');

      return result;
    } catch (error) {
      logger.error(`LLMサービスでエラーが発生しました: ${error}`);
      throw new Error('LLMとの連携中にエラーが発生しました。');
    }
  }
}
