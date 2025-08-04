import { LLMService } from './llm_service';
import { logger } from '../utils/logger';

// pipeチェーンの最終出力でinvokeを直接持つようにモック
const mockInvoke = jest.fn();
const mockPipe = jest.fn();

mockPipe.mockImplementation(function () {
  // pipeチェーンの最後だけinvokeを持つ（テスト用）
  return { pipe: mockPipe, invoke: mockInvoke };
});

jest.mock('@langchain/google-genai', () => {
  return {
    ChatGoogleGenerativeAI: jest.fn().mockImplementation(() => ({
      pipe: mockPipe,
    })),
  };
});

jest.mock('@langchain/core/prompts', () => {
  return {
    PromptTemplate: jest.fn().mockImplementation(() => ({
      pipe: mockPipe,
    })),
  };
});

jest.mock('@langchain/core/output_parsers', () => {
  return {
    JsonOutputParser: jest.fn().mockImplementation(() => ({
      getFormatInstructions: jest.fn().mockReturnValue('format_instructions'),
      pipe: mockPipe,
    })),
  };
});

describe('LLMService', () => {
  let service: LLMService;

  beforeEach(() => {
    service = new LLMService();
    mockInvoke.mockReset();
  });

  it('should be defined', () => {
    // インスタンスが生成できることを確認
    expect(service).toBeDefined();
  });

  describe('generateJson', () => {
    it('should return parsed JSON from the LLM', async () => {
      // LLMの応答が正常な場合のテスト
      mockInvoke.mockResolvedValue({ foo: 'bar' });
      const prompt = 'prompt: {input}\n{format_instructions}';
      const input = { input: 'test' };
      const result = await service.generateJson<{ foo: string }>(prompt, input);
      expect(result).toEqual({ foo: 'bar' });
    });

    it('should throw an error and log if LLM fails', async () => {
      // LLMがエラーを返した場合の例外・ロギングのテスト
      const error = new Error('fail');
      mockInvoke.mockRejectedValue(error);
      const loggerSpy = jest.spyOn(logger, 'error').mockImplementation();
      const prompt = 'prompt: {input}\n{format_instructions}';
      const input = { input: 'test' };
      await expect(service.generateJson(prompt, input)).rejects.toThrow('LLMとの連携中にエラーが発生しました。');
      expect(loggerSpy).toHaveBeenCalled();
      loggerSpy.mockRestore();
    });
  });
});
