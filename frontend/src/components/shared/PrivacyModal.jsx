import React, { useState, useEffect } from 'react';
import './PrivacyModal.css';

const PRIVACY_CONTENT = `
一、引言
欢迎使用本皮影动画创作平台（以下简称「本平台」）。我们重视并保护您的个人信息与隐私。请您在使用本平台前仔细阅读本《隐私条款》；使用即表示您已阅读、理解并同意本条款。

二、我们收集的信息
2.1 您主动提供的信息：注册或使用本平台时，您可能提供用户名、邮箱、密码等账号信息，以及您上传的创作内容（如角色、场景、剧本、音视频等）。
2.2 自动收集的信息：为保障服务正常运行，我们可能收集设备类型、浏览器类型、IP 地址、访问时间等必要的技术信息。
2.3 摄像头与动作捕捉：若您使用「动作捕捉」相关功能，我们会实时处理摄像头画面以生成动作数据；相关数据可在本地处理或经后端进行技术分析，我们不会将您的面部或身体影像用于识别个人身份或对外提供。

三、信息的使用
我们仅将收集的信息用于：向您提供本平台功能与服务、改进产品体验、保障账号与系统安全、以及法律法规允许的用途。未经您同意，我们不会将您的个人信息出售或向第三方提供用于其营销目的。

四、信息的存储与安全
我们采用合理的技术与管理措施保护您的个人信息，防止未经授权的访问、使用或泄露。您的账号信息与创作内容存储于本平台控制的服务器或您知晓的本地环境中。

五、信息的共享与披露
除以下情况外，我们不会与第三方共享您的个人信息：（1）经您明确同意；（2）为完成您请求的服务所必需的合作方（我们要求其严格保密）；（3）法律法规要求或为保护本平台及其他用户合法权益所必需。

六、您的权利
您有权查询、更正、删除您的账号信息及部分个人数据；您也可以选择不再使用本平台并注销账号。关于具体操作，可通过本平台提供的设置或联系运营方实现。

七、未成年人保护
若您为未成年人，请在监护人同意的前提下使用本平台。我们不会主动收集未成年人的敏感信息。

八、条款更新
我们可能适时修订本《隐私条款》，修订后的条款将在本平台公布。若您继续使用本平台，即视为接受更新后的条款。

九、联系我们
如您对本隐私条款或个人信息处理有任何疑问，请通过本平台公示的联系方式与我们联系。

最后更新日期：2026 年 2 月
`;

export default function PrivacyModal({ isOpen, onClose }) {
  const [agreed, setAgreed] = useState(false);

  useEffect(() => {
    if (isOpen) setAgreed(false);
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="privacy-modal-overlay" onClick={onClose}>
      <div className="privacy-modal" onClick={(e) => e.stopPropagation()}>
        <div className="privacy-modal-header">
          <h2>隐私条款</h2>
          <button type="button" className="privacy-modal-close" onClick={onClose} aria-label="关闭">×</button>
        </div>
        <div className="privacy-modal-body">
          <pre className="privacy-content">{PRIVACY_CONTENT.trim()}</pre>
        </div>
        <div className="privacy-modal-footer">
          <label className="privacy-agree-label">
            <input
              type="checkbox"
              checked={agreed}
              onChange={(e) => setAgreed(e.target.checked)}
            />
            <span>我已阅读并同意上述隐私条款</span>
          </label>
          <button
            type="button"
            className="privacy-agree-btn"
            onClick={onClose}
            disabled={!agreed}
          >
            确认并关闭
          </button>
        </div>
      </div>
    </div>
  );
}
