import lejos.nxt.Motor;

public class MotorRun {
    private static final int SPEED = 360; // degrees per second

    public static void main(String[] args) {
        Motor.A.forward();
        Motor.A.setSpeed(SPEED);

        while (true) {
            // Keep the program alive so the motor keeps running.
        }
    }
}
