"""
live_visualizer.py - リアルタイム可視化

matplotlib を使ってシミュレーションの状態をリアルタイムに表示
"""

from io import BytesIO
from pathlib import Path
from typing import Dict, Any
import matplotlib.pyplot as plt
from PIL import Image
import numpy as np
import imageio


class LiveVisualizer:
    """
    シミュレーション状態をリアルタイムに可視化するクラス
    """
    
    def __init__(self, width: int, height: int, interval_ms: int = 100, save_animation: bool = False, save_video: bool = False):
        """
        ビジュアライザーを初期化
        
        Args:
            width: グリッドの幅
            height: グリッドの高さ
            interval_ms: 描画の更新間隔（ミリ秒）
            save_animation: GIF アニメーションを保存するかどうか
            save_video: MP4 動画を保存するかどうか
        """
        self.width = width
        self.height = height
        self.interval_ms = interval_ms
        self.save_animation = save_animation
        self.save_video = save_video
        self.frames: list[Image.Image] = []
        
        # Figure と Axis を作成
        self.fig, self.ax = plt.subplots(figsize=(10, 10))
        self.fig.suptitle("Daphnia Evolution Simulation", fontsize=16)
        
        # Axis の設定
        self.ax.set_xlim(-0.5, width - 0.5)
        self.ax.set_ylim(-0.5, height - 0.5)
        self.ax.set_aspect("equal")
        self.ax.invert_yaxis()  # y軸を反転（画面座標に合わせる）
        self.ax.set_xlabel("X")
        self.ax.set_ylabel("Y")
        self.ax.grid(True, alpha=0.3)
        
        # タイトル用のテキストオブジェクト
        self.title_text = self.ax.text(
            0.5, -0.08,
            "",
            transform=self.ax.transAxes,
            ha="center",
            fontsize=12
        )
        
        # 描画用のオブジェクト
        self.food_scatter = None
        self.organism_scatter = None
        self.reproductible_scatter = None
    
    def update(self, state: Dict[str, Any]) -> None:
        """
        シミュレーション状態に基づいて描画を更新
        
        Args:
            state: get_state() から返されたシミュレーション状態
        """
        # 前のプロット要素をクリア
        self.ax.clear()
        self.ax.set_xlim(-0.5, self.width - 0.5)
        self.ax.set_ylim(-0.5, self.height - 0.5)
        self.ax.set_aspect("equal")
        self.ax.invert_yaxis()
        self.ax.set_xlabel("X")
        self.ax.set_ylabel("Y")
        self.ax.grid(True, alpha=0.3)
        
        # 食料を描画（緑色の点）
        food_positions = state["food_positions"]
        if food_positions:
            food_x = [pos[0] for pos in food_positions]
            food_y = [pos[1] for pos in food_positions]
            self.ax.scatter(
                food_x, food_y,
                c="green", s=20, alpha=0.6, marker="o", label="Food"
            )
        
        # 個体を描画
        organism_positions = state["organism_positions"]
        organism_states = state["organism_states"]
        
        if organism_positions:
            org_x = [pos[0] for pos in organism_positions]
            org_y = [pos[1] for pos in organism_positions]
            
            # 通常の個体（青色）
            normal_indices = [
                i for i, s in enumerate(organism_states) if s == "normal"
            ]
            if normal_indices:
                normal_x = [org_x[i] for i in normal_indices]
                normal_y = [org_y[i] for i in normal_indices]
                self.ax.scatter(
                    normal_x, normal_y,
                    c="blue", s=50, alpha=0.7, marker="o", label="Organism"
                )
            
            # 繁殖可能な個体（赤色）
            repro_indices = [
                i for i, s in enumerate(organism_states) if s == "can_reproduce"
            ]
            if repro_indices:
                repro_x = [org_x[i] for i in repro_indices]
                repro_y = [org_y[i] for i in repro_indices]
                self.ax.scatter(
                    repro_x, repro_y,
                    c="red", s=50, alpha=0.7, marker="o", label="Ready to Reproduce"
                )
        
        # タイトルに統計情報を表示
        title_str = (
            f"Step: {state['step']} | "
            f"Population: {state['population_size']} (B:{state['birth_count']} D:{state['death_count']}) | "
            f"Food: {state['food_count']} | "
            f"Avg Energy: {state['average_energy']:.2f} | "
            f"Avg Age: {state['average_age']:.2f}"
        )
        self.ax.set_title(title_str, fontsize=12, pad=20)
        
        # legendを追加
        self.ax.legend(loc="upper right")
        
        # 描画を更新
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

        if self.save_animation or self.save_video:
            self.capture_frame()

    def capture_frame(self) -> None:
        """現在のFigureをPNGとしてキャプチャし、フレームリストに追加する"""
        buffer = BytesIO()
        self.fig.savefig(buffer, format="png", dpi=100)
        buffer.seek(0)
        image = Image.open(buffer).convert("RGB")
        self.frames.append(image)

    def save_gif_file(self, path: str, interval_ms: int) -> None:
        """保存された状態から GIF ファイルを生成"""
        if not self.frames:
            return
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        duration = max(1, interval_ms)

        # Pillow を使って共通パレットで量子化し GIF を作成（色揺れ防止）
        width, height = self.frames[0].size
        combined = Image.new("RGB", (width * len(self.frames), height))
        for i, f in enumerate(self.frames):
            combined.paste(f.convert("RGB"), (i * width, 0))

        palette_source = combined.convert("P", palette=Image.ADAPTIVE, colors=256)

        # 各フレームを共通パレットで量子化
        quantized_frames = [f.convert("RGB").quantize(palette=palette_source) for f in self.frames]
        common_palette = palette_source.getpalette()
        for q in quantized_frames:
            q.putpalette(common_palette)

        # 保存
        quantized_frames[0].save(
            str(output_path),
            save_all=True,
            append_images=quantized_frames[1:],
            duration=duration,
            loop=0,
            disposal=2,
            optimize=False,
            background=0,
        )

    def save_video_file(self, path: str, interval_ms: int) -> None:
        """保存された状態から MP4 動画を生成"""
        if not self.frames:
            return
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fps = max(1, 1000 / max(1, interval_ms))

        frames_np = [np.array(frame.convert("RGB")) for frame in self.frames]
        imageio.mimsave(
            str(output_path),
            frames_np,
            fps=fps,
            format="FFMPEG",
            codec="libx264",
            ffmpeg_params=["-pix_fmt", "yuv420p"],
        )

    def save_animation_file(self, path: str, interval_ms: int) -> None:
        self.save_gif_file(path, interval_ms)

    def close(self) -> None:
        """ビジュアライザーを閉じる"""
        plt.close(self.fig)


def run_live_visualization(sim) -> None:
    """
    シミュレーションをリアルタイム可視化しながら実行
    
    Args:
        sim: Simulation オブジェクト
    """
    # ビジュアライザーを作成
    env_config = sim.config["environment"]
    vis_config = sim.config.get("visualization", {})
    
    interval_ms = vis_config.get("interval_ms", 100)
    save_animation = vis_config.get("save_animation", False)
    save_video = vis_config.get("save_video", False)
    animation_path = vis_config.get("animation_path", "results/simulation.gif")
    video_path = vis_config.get("video_path", "results/simulation.mp4")
    
    print(f"リアルタイム可視化ウィンドウを作成中...")
    visualizer = LiveVisualizer(
        width=env_config["width"],
        height=env_config["height"],
        interval_ms=interval_ms,
        save_animation=save_animation,
        save_video=save_video
    )
    
    # インタラクティブモードを有効化
    plt.ion()
    
    # ウィンドウを表示
    plt.show(block=False)
    print(f"✓ リアルタイム可視化ウィンドウが開きました")
    print(f"  グリッドサイズ: {env_config['width']}x{env_config['height']}")
    print(f"  描画更新間隔: {interval_ms}ms")
    print(f"  ウィンドウを閉じるか Ctrl+C で終了してください\n")
    
    total_steps = sim.config["simulation"]["steps"]
    
    try:
        for step_num in range(total_steps):
            # 1ステップ実行
            sim.step()
            
            # 状態を取得して描画を更新
            state = sim.get_state()
            visualizer.update(state)
            
            # 描画を更新
            plt.pause(interval_ms / 1000.0)
            
            # ウィンドウを閉じられたら終了
            if not plt.fignum_exists(visualizer.fig.number):
                print("\nウィンドウが閉じられました")
                break
            
            # 定期的に標準出力に情報を表示
            if (step_num + 1) % 100 == 0:
                print(f"Step {step_num + 1}/{total_steps} - Population: {state['population_size']}, Food: {state['food_count']}")
    
    except KeyboardInterrupt:
        print("\n\nシミュレーションが中断されました")
    
    finally:
        if save_animation:
            try:
                visualizer.save_animation_file(animation_path, interval_ms)
                print(f"アニメーションを保存しました: {animation_path}")
            except Exception as exc:
                print(f"アニメーションの保存に失敗しました: {exc}")

        if save_video:
            try:
                visualizer.save_video_file(video_path, interval_ms)
                print(f"動画を保存しました: {video_path}")
            except Exception as exc:
                print(f"動画の保存に失敗しました: {exc}")

        visualizer.close()
        print(f"\n=== シミュレーション完了 ===")
        print(f"実行ステップ: {sim.current_step}")
        print(f"最終個体数: {len(sim.organisms)}")
        print(f"最終食料数: {sim.environment.food_count()}")
