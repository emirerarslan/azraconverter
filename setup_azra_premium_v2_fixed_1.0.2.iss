; ============================================================
; AZRA CONVERTER - PREMIUM DARK / GOLD SETUP
; ============================================================

#define MyAppName "AZRA CONVERTER"
#define MyAppVersion "1.0.1"
#define MyAppPublisher "Azra Gold"
#define MyAppExeName "AZRA CONVERTER.exe"
#define MyAppIcon "azra_gold.ico"

[Setup]
AppId={{B8A6F4D1-7B35-4E2A-9B71-AZRA2026CONV}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Azra Gold\Azra Converter
DisableDirPage=yes
DefaultGroupName=Azra Converter
DisableProgramGroupPage=yes
OutputDir=installer
OutputBaseFilename=AZRA-CONVERTER-SETUP-1.0.1
SetupIconFile={#MyAppIcon}
UninstallDisplayIcon={app}\{#MyAppIcon}
WizardStyle=modern
WizardImageFile=azra_setup.bmp
WizardSmallImageFile=azra_setup_small.bmp
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
Uninstallable=yes
VersionInfoCompany=Azra Gold
VersionInfoDescription=Azra Converter Kurulum
VersionInfoProductName=Azra Converter
VersionInfoProductVersion={#MyAppVersion}

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "desktopicon"; Description: "Masaüstü kısayolu oluştur"; GroupDescription: "Kısayollar:"; Flags: checkedonce

[Files]
; EXE ve tüm runtime dosyaları
Source: "dist\AZRA CONVERTER\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Güncelleme denetiminin GitHub adresi, program klasöründe düzenlenebilir kalır.
Source: "update_config.json"; DestDir: "{app}"; Flags: ignoreversion

; ICO dosyasını ayrıca garanti altına alıyoruz.
Source: "azra_gold.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Kısayol doğrudan kurulum klasöründeki ICO'yu kullanır.
Name: "{autodesktop}\Azra Converter"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppIcon}"; Tasks: desktopicon
Name: "{autoprograms}\Azra Converter"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppIcon}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Azra Converter'ı şimdi çalıştır"; Flags: nowait postinstall skipifsilent

[Code]
const
  BG        = $000B0B0B;
  PANEL     = $00131313;
  PANEL2    = $001B1A18;
  GOLD      = $0068B5D8;
  GOLD2     = $00A8D9F2;
  TEXT      = $00FFFDF8;
  MUTED     = $00B9B2A8;

procedure PaintPanel(P: TPanel; C: TColor);
begin
  P.Color := C;
  P.ParentBackground := False;
end;

procedure StyleStatic(S: TNewStaticText; C: TColor; Size: Integer; Bold: Boolean);
begin
  S.Font.Name := 'Segoe UI';
  S.Font.Size := Size;
  S.Font.Color := C;
  if Bold then S.Font.Style := [fsBold]
  else S.Font.Style := [];
end;

procedure StyleAllControls(W: TWinControl);
var
  I: Integer;
  C: TControl;
begin
  for I := 0 to W.ControlCount - 1 do
  begin
    C := W.Controls[I];

    if C is TPanel then
      PaintPanel(TPanel(C), PANEL);

    if C is TNewStaticText then
      StyleStatic(TNewStaticText(C), TEXT, 10, False);

    if C is TNewButton then
    begin
      TNewButton(C).Font.Name := 'Segoe UI';
      TNewButton(C).Font.Size := 10;
      TNewButton(C).Font.Color := TEXT;
      TNewButton(C).Font.Style := [fsBold];
    end;

    if C is TNewCheckListBox then
    begin
      TNewCheckListBox(C).Font.Name := 'Segoe UI';
      TNewCheckListBox(C).Font.Size := 10;
      TNewCheckListBox(C).Font.Color := TEXT;
      TNewCheckListBox(C).Color := PANEL;
      TNewCheckListBox(C).ParentColor := False;
    end;

    if C is TWinControl then
      StyleAllControls(TWinControl(C));
  end;
end;

procedure InitializeWizard;
begin
  WizardForm.Color := BG;
  WizardForm.Font.Name := 'Segoe UI';
  WizardForm.Font.Color := TEXT;
  WizardForm.MainPanel.Color := BG;
  WizardForm.MainPanel.ParentBackground := False;

  WizardForm.WelcomeLabel1.Font.Name := 'Segoe UI';
  WizardForm.WelcomeLabel1.Font.Size := 21;
  WizardForm.WelcomeLabel1.Font.Style := [fsBold];
  WizardForm.WelcomeLabel1.Font.Color := GOLD2;

  WizardForm.WelcomeLabel2.Font.Name := 'Segoe UI';
  WizardForm.WelcomeLabel2.Font.Size := 10;
  WizardForm.WelcomeLabel2.Font.Color := MUTED;

  WizardForm.PageNameLabel.Font.Name := 'Segoe UI';
  WizardForm.PageNameLabel.Font.Size := 17;
  WizardForm.PageNameLabel.Font.Style := [fsBold];
  WizardForm.PageNameLabel.Font.Color := GOLD2;

  WizardForm.PageDescriptionLabel.Font.Name := 'Segoe UI';
  WizardForm.PageDescriptionLabel.Font.Size := 10;
  WizardForm.PageDescriptionLabel.Font.Color := MUTED;

  WizardForm.FinishedHeadingLabel.Font.Name := 'Segoe UI';
  WizardForm.FinishedHeadingLabel.Font.Size := 19;
  WizardForm.FinishedHeadingLabel.Font.Style := [fsBold];
  WizardForm.FinishedHeadingLabel.Font.Color := GOLD2;

  WizardForm.FinishedLabel.Font.Name := 'Segoe UI';
  WizardForm.FinishedLabel.Font.Size := 11;
  WizardForm.FinishedLabel.Font.Color := TEXT;

  WizardForm.BeveledLabel.Color := BG;
  WizardForm.StatusLabel.Font.Name := 'Segoe UI';
  WizardForm.StatusLabel.Font.Size := 9;
  WizardForm.StatusLabel.Font.Color := MUTED;

  { Ek işlemler / checkbox alanı: koyu zemin + belirgin yazı }
  WizardForm.TasksList.Font.Name := 'Segoe UI';
  WizardForm.TasksList.Font.Size := 10;
  WizardForm.TasksList.Font.Color := TEXT;
  WizardForm.TasksList.Color := PANEL;
  WizardForm.TasksList.ParentColor := False;

  StyleAllControls(WizardForm);

  WizardForm.NextButton.Caption := 'İLERİ  ›';
  WizardForm.BackButton.Caption := '‹  GERİ';
  WizardForm.CancelButton.Caption := 'İPTAL';
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpWelcome then
    WizardForm.NextButton.Caption := 'BAŞLA  ›'
  else if CurPageID = wpFinished then
    WizardForm.NextButton.Caption := 'BİTİR'
  else
    WizardForm.NextButton.Caption := 'İLERİ  ›';

  WizardForm.Color := BG;
  WizardForm.MainPanel.Color := BG;

  { Sayfa değişiminde de checkbox alanının stilini koru }
  WizardForm.TasksList.Font.Color := TEXT;
  WizardForm.TasksList.Color := PANEL;
  WizardForm.TasksList.ParentColor := False;

  StyleAllControls(WizardForm);
end;
