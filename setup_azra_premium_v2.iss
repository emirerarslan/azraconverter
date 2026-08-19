#pragma codepage "utf-8"
; ============================================================
; CONVERTER - BLACK / GOLD SETUP
; ============================================================

#define MyAppName "ConverteR"
#define MyAppVersion "1.1.17"
#define MyAppPublisher "ConverteR"
#define MyAppExeName "ConverteR.exe"
#define MyAppIcon "converter-new.ico"

[Setup]
AppId={{B8A6F4D1-7B35-4E2A-9B71-AZRA2026CONV}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\ConverteR
DisableDirPage=yes
DefaultGroupName=ConverteR
DisableProgramGroupPage=yes
OutputDir=installer
OutputBaseFilename=CONVERTER-SETUP-1.1.17
SetupIconFile={#MyAppIcon}
UninstallDisplayIcon={app}\{#MyAppIcon}
WizardStyle=modern
WizardImageFile=setup_black.bmp
WizardSmallImageFile=setup_black_small.bmp
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
Uninstallable=yes
VersionInfoCompany=ConverteR
VersionInfoDescription=ConverteR Kurulum
VersionInfoProductName=ConverteR
VersionInfoProductVersion={#MyAppVersion}

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "desktopicon"; Description: "Masaüstü kısayolu oluştur"; GroupDescription: "Kısayollar:"; Flags: checkedonce

[Files]
; EXE ve tüm runtime dosyaları
Source: "dist\ConverteR\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; ICO dosyasını ayrıca garanti altına alıyoruz.
Source: "converter-new.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "setup_flag.bmp"; Flags: dontcopy
Source: "setup_emir_photo.bmp"; Flags: dontcopy

[Icons]
; Kısayol doğrudan kurulum klasöründeki ICO'yu kullanır.
Name: "{autodesktop}\ConverteR"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppIcon}"; Tasks: desktopicon
Name: "{autoprograms}\ConverteR"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppIcon}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "ConverteR'ı şimdi çalıştır"; Flags: nowait postinstall skipifsilent

[Code]
const
  BG        = $000B0B0B;
  PANEL     = $00000000;
  PANEL2    = $00000000;
  GOLD      = $0068B5D8;
  GOLD2     = $00A8D9F2;
  TEXT      = $00A8D9F2;
  MUTED     = $0068B5D8;

var
  FlagImage: TBitmapImage;
  PhotoImage: TBitmapImage;

procedure UpdateHeaderImages;
begin
  FlagImage.SetBounds(16, 16, 84, 56);
  PhotoImage.SetBounds(WizardForm.ClientWidth - 88, 12, 72, 72);
  FlagImage.BringToFront;
  PhotoImage.BringToFront;
end;

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

    if C is TWinControl then
      StyleAllControls(TWinControl(C));
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  OldUninstaller: String;
  ResultCode: Integer;
begin
  Result := '';
  OldUninstaller := ExpandConstant('{pf}\Azra Converter\unins000.exe');

  { Eski 1.0 kurulumu farklı AppId ve klasör kullandığı için yeni sürümün
    yanında kalabiliyordu. Yeni dosyalar kurulmadan önce sessizce kaldır. }
  if FileExists(OldUninstaller) then
  begin
    if not Exec(OldUninstaller,
      '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART', '', SW_HIDE,
      ewWaitUntilTerminated, ResultCode) then
      Log('Eski Azra Converter kaldırıcısı başlatılamadı.')
    else if ResultCode <> 0 then
      Log(Format('Eski Azra Converter kaldırıcısı %d koduyla tamamlandı.', [ResultCode]));
  end;

  DeleteFile(ExpandConstant('{commonprograms}\AZRA CONVERTER\AZRA CONVERTER.lnk'));
  RemoveDir(ExpandConstant('{commonprograms}\AZRA CONVERTER'));
  DeleteFile(ExpandConstant('{commondesktop}\AZRA CONVERTER.lnk'));
end;

procedure InitializeWizard;
begin
  ExtractTemporaryFile('setup_flag.bmp');
  ExtractTemporaryFile('setup_emir_photo.bmp');

  WizardForm.Color := BG;
  WizardForm.Font.Name := 'Segoe UI';
  WizardForm.Font.Color := TEXT;
  WizardForm.MainPanel.Color := BG;
  WizardForm.MainPanel.ParentBackground := False;

  FlagImage := TBitmapImage.Create(WizardForm);
  FlagImage.Parent := WizardForm;
  FlagImage.Bitmap.LoadFromFile(ExpandConstant('{tmp}\setup_flag.bmp'));
  FlagImage.Stretch := True;
  FlagImage.SetBounds(16, 16, 84, 56);

  PhotoImage := TBitmapImage.Create(WizardForm);
  PhotoImage.Parent := WizardForm;
  PhotoImage.Bitmap.LoadFromFile(ExpandConstant('{tmp}\setup_emir_photo.bmp'));
  PhotoImage.Stretch := True;
  UpdateHeaderImages;

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

  StyleAllControls(WizardForm);
  UpdateHeaderImages;

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
  StyleAllControls(WizardForm);
  UpdateHeaderImages;
end;
